import unittest
import pandas as pd
import os
from collections import Counter

from business import (
    _apply_economy_scoring, 
    _apply_inspiration_scoring, 
    _calculate_status,  
    _get_target_months, 
    _get_product_months,
    get_menu_stats, 
    get_seasonal_df, 
    get_general_recommendations, 
    get_menu_recommendations
)

class TestRecommendationSystem(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):

        cls.db_path = 'farm_data.db'
        cls.json_path = 'menu_result.json'
        
        if not os.path.exists(cls.db_path):
            raise FileNotFoundError(f"База {cls.db_path} не найдена!")
            
        if not os.path.exists(cls.json_path):
            raise FileNotFoundError(f"Файл {cls.json_path} не найден!")


    def test_apply_economy_scoring(self):
        """Тестируем логарифмическую формулу для Экономии"""
        test_df = pd.DataFrame({
            'main_ingredient': ['лук', 'трюфель'],
            'mentions': [10, 1], 
            'rarity_score': [2, 12],
            'is_premium': [0, 1]
        })
        
        result_df = _apply_economy_scoring(test_df)
        
        self.assertIn('score', result_df.columns)
        scores = result_df['score'].tolist()
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_apply_inspiration_scoring(self):
        """Тестируем умножение для Вдохновения"""
        test_df = pd.DataFrame({
            'main_ingredient': ['базовая_клубника', 'премиум_клубника'],
            'rarity_score': [10, 10],
            'is_premium': [0, 1]
        })
        
        result_df = _apply_inspiration_scoring(test_df)
        
        self.assertEqual(result_df.iloc[0]['main_ingredient'], 'премиум_клубника')
        self.assertEqual(result_df.iloc[0]['score'], 30.0)
        self.assertEqual(result_df.iloc[1]['score'], 20.0)

    def test_calculate_status(self):
        """Тестируем логику выдачи статусов (Premium > Rare > Base)"""
        self.assertEqual(_calculate_status({'is_premium': 1, 'rarity_score': 15}), "premium")
        self.assertEqual(_calculate_status({'is_premium': 0, 'rarity_score': 10}), "rare")
        self.assertEqual(_calculate_status({'is_premium': 0, 'rarity_score': 5}), "base")

    def test_get_target_months(self):
        """Тестируем правильное определение выбранного периода"""
        self.assertEqual(_get_target_months(6, 8), [6, 7, 8])
        self.assertEqual(_get_target_months(11, 2), [11, 12, 1, 2])

    def test_get_product_months(self):
        row = {f'month_{m}': (1 if m in [5, 6, 7] else 0) for m in range(1, 13)}
        self.assertEqual(_get_product_months(row), [5, 6, 7])
        
        row_empty = {f'month_{m}': 0 for m in range(1, 13)}
        self.assertEqual(_get_product_months(row_empty), [])
        
        row_all = {f'month_{m}': 1 for m in range(1, 13)}
        self.assertEqual(_get_product_months(row_all), list(range(1, 13)))
    

    def test_get_menu_stats(self):
        """Тестируем, правильно ли читается JSON-файл от ML"""
        ingredient_counts, total_dishes, cuisine_type = get_menu_stats(self.json_path)
        self.assertIsInstance(ingredient_counts, Counter)
        self.assertGreater(total_dishes, 0)
        self.assertIsInstance(cuisine_type, str)
        self.assertEqual(cuisine_type, "Азербайджанская")

    def test_get_seasonal_df_normal(self):
        """Тестируем стандартный сезон """
        df = get_seasonal_df(5, 8, self.db_path)
        if not df.empty:
            self.assertTrue( ((df['month_5'] == 1) | (df['month_6'] == 1) | (df['month_7'] == 1) | (df['month_8'] == 1)).any() )

    def test_get_seasonal_df_winter_wrap(self):
        """Тестируем перехлест (Ноябрь-Февраль)"""
        df = get_seasonal_df(11, 2, self.db_path)
        self.assertIsInstance(df, pd.DataFrame)

    def test_get_general_recommendations(self):
        """Интеграционный тест: Каталог без меню"""
        res = get_general_recommendations(6, 8, self.db_path)
        
        self.assertIn("selected_period", res)
        self.assertIn("recommendations", res)
        
        self.assertLessEqual(len(res["recommendations"]), 15)
        
        if res["recommendations"]:
            first_card = res["recommendations"][0]
            expected_keys = ["product_id", "product_name", "farmer_name", "link", "status", "novelty_score", "season_months", "reason"]
            for key in expected_keys:
                self.assertIn(key, first_card)

    def test_get_menu_recommendations(self):
        """Интеграционный тест: Анализ реального меню шеф-повара"""
        res = get_menu_recommendations(self.json_path, 6, 8, self.db_path)
        
        self.assertIn("cuisine_type", res)
        self.assertIn("total_dishes", res)
        self.assertIn("recommendations", res)
        
        if res["recommendations"]:
            first_card = res["recommendations"][0]
            self.assertIn("recommendation_type", first_card)
            self.assertIn(first_card["recommendation_type"], ["economy", "inspiration"])

if __name__ == '__main__':
    unittest.main(verbosity=2)