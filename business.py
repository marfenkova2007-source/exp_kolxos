import json
from collections import Counter
import sqlite3
import pandas as pd
import numpy as np

DEFAULT_DB_PATH = 'farm_data.db'
DEFAULT_CUISINE = 'Авторская'

# Настройки выдачи
GENERAL_REC_LIMIT = 15
ECONOMY_LIMIT = 7
INSPIRATION_LIMIT = 8
BASE_NOVELTY_SCORE = 100.0

# Настройки скоринга 
ECONOMY_MENTION_WEIGHT = 10
ECONOMY_PREMIUM_BONUS = 5
INSPIRATION_RARITY_WEIGHT = 2
INSPIRATION_PREMIUM_MULT = 1.5
RARE_THRESHOLD = 10  # Порог редкости для статуса 'rare'

def get_general_recommendations(start_month: int, end_month: int, db_path: str = DEFAULT_DB_PATH) -> dict:
    """Генерирует топ-15 лучших сезонных предложений без привязки к конкретному меню. Используется для общего каталога вдохновения"""
    target_months = _get_target_months(start_month, end_month)
    df = get_seasonal_df(start_month, end_month, db_path)
    
    if df.empty:
        return {
            "selected_period": {"start_month": start_month, "end_month": end_month},
            "recommendations": []
        }
    df = _apply_inspiration_scoring(df)
    df = df.drop_duplicates(subset=['main_ingredient', 'shop_name']).head(GENERAL_REC_LIMIT)
    result_list = _build_recommendation_cards(df, target_months)
    return {
        "selected_period": {"start_month": start_month, "end_month": end_month},
        "recommendations": result_list
    }

def get_menu_recommendations(menu_json_path: str, start_month: int, end_month: int, db_path: str = DEFAULT_DB_PATH) -> dict:
    """Анализирует меню и возвращает 15 продуктов. 7 продуктов для экономии на текущем и 8 продуктов для новых идей"""
    target_months = _get_target_months(start_month, end_month)
    ingredient_counts, total_dishes, cuisine_type = get_menu_stats(menu_json_path)
    
    df = get_seasonal_df(start_month, end_month, db_path)
    if df.empty: 
        return {
            "cuisine_type": cuisine_type,
            "total_dishes": total_dishes,
            "selected_period": {"start_month": start_month, "end_month": end_month},
            "recommendations": []
        }


    df['mentions'] = df['main_ingredient'].map(ingredient_counts).fillna(0)
    
    df['novelty_score'] = BASE_NOVELTY_SCORE - (df['mentions'] / total_dishes * 100.0 if total_dishes > 0 else 0)

    df_economy = df[df['mentions'] > 0].copy()
    
    if not df_economy.empty:
        df_economy = _apply_economy_scoring(df_economy)
        df_economy = df_economy.drop_duplicates(subset=['main_ingredient', 'shop_name']).head(ECONOMY_LIMIT)

    df_new = df[df['mentions'] == 0].copy()
    
    if not df_new.empty:
        df_new = _apply_inspiration_scoring(df_new)
        df_new = df_new.drop_duplicates(subset=['main_ingredient', 'shop_name']).head(INSPIRATION_LIMIT)

    final_df = pd.concat([df_economy, df_new])
    result_list = _build_recommendation_cards(final_df, target_months)
        
    return {
        "cuisine_type": cuisine_type,
        "total_dishes": total_dishes,
        "selected_period": {
            "start_month": start_month,
            "end_month": end_month
        },
        "recommendations": result_list
    }

def get_menu_stats(menu_json_path: str) -> tuple[Counter, int, str]:
    """Для статистики из JSON-файла меню: подсчитывает количество  каждого ингредиента, общее число блюд и тип кухни"""
    with open(menu_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    cuisine_type = data.get('cuisine_type', DEFAULT_CUISINE)
    dishes = data.get('dishes', [])
    total_dishes = len(dishes)
    all_ingredients = []
    for dish in dishes:
        for ing in dish.get('ingredients', []):
            main_ing = ing.get('main_ingredient')
            if main_ing:
                all_ingredients.append(main_ing)
    ingredient_counts = Counter(all_ingredients)
    return ingredient_counts, total_dishes, cuisine_type

def get_seasonal_df(start_month: int, end_month: int, db_path: str = DEFAULT_DB_PATH) -> pd.DataFrame:
    """ Выгружает из БД все продукты, доступные хотя бы в один из месяцев  выбранного пользователем периода"""
    target_months = _get_target_months(start_month, end_month)
    conditions = [f"month_{m} = 1" for m in target_months]
    where_clause = " OR ".join(conditions)
    query = f"SELECT * FROM products WHERE {where_clause}"
    
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn)
    return df

def _apply_economy_scoring(df: pd.DataFrame) -> pd.DataFrame:
    """Логарифмический скоринг часто встречающихся в меню продуктов для удешевления общей стоимости меню"""
    df_scored = df.copy()
    df_scored['score'] = (
        (np.log1p(df_scored['mentions']) * ECONOMY_MENTION_WEIGHT) + 
        df_scored['rarity_score'] + 
        (df_scored['is_premium'] * ECONOMY_PREMIUM_BONUS)
    )
    return df_scored.sort_values(by='score', ascending=False)

def _apply_inspiration_scoring(df: pd.DataFrame) -> pd.DataFrame:
    """Приоретизация редких и премиальных продуктов для создания сезонных новинок"""
    df_scored = df.copy()
    premium_multiplier = df_scored['is_premium'].map({1: INSPIRATION_PREMIUM_MULT, 0: 1.0})
    df_scored['score'] = (df_scored['rarity_score'] * INSPIRATION_RARITY_WEIGHT) * premium_multiplier
    return df_scored.sort_values(by='score', ascending=False)

def _build_recommendation_cards(df: pd.DataFrame, target_months: list[int]) -> list[dict]:
    """Формирует стандартизированный список словарей"""
    result = []
    for row in df.to_dict('records'): 
        reason_type = "economy" if row.get('mentions', 0) > 0 else "inspiration"
        
        result.append({
            "product_id": row['product_id'],
            "product_name": row['name_product'],
            "farmer_name": row['shop_name'],
            "link": row['url_product'],
            "status": _calculate_status(row),
            "novelty_score": round(row.get('novelty_score', BASE_NOVELTY_SCORE), 1),
            "season_months": _extract_intersection_months(row, target_months),            
            "recommendation_type": reason_type,
            "reason": ""
        })
    return result

def _get_target_months(start_month: int, end_month: int) -> list[int]:
    """Отдает список порядковых номеров месяцев в выбранном диапазоне"""
    if start_month <= end_month:
        return list(range(start_month, end_month + 1))
    else:
        return list(range(start_month, 13)) + list(range(1, end_month + 1))
    
def _calculate_status(row: dict) -> str:
    """Определяет категорию товара: base, rare или premium"""
    if row['is_premium'] == 1:
        return "premium"
    elif row['rarity_score'] >= RARE_THRESHOLD:
        return "rare"
    else:
        return "base"
    
def _extract_intersection_months(row: dict, target_months: list[int]) -> list[int]:
    """Находит общие месяцы между периодом доступности продукта и сезоном, который выбрал пользователь"""
    product_months = [m for m in range(1, 13) if row[f'month_{m}'] == 1]
    return [m for m in product_months if m in target_months]



