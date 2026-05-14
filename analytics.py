import logging
import json
import os
import logging
from google import genai
from dotenv import load_dotenv
from pdf_extractor import extract_text_from_pdf

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=GOOGLE_API_KEY)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_ingredients_dict(file_path: str = "ingredients_list_for_yulia.txt") -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Ошибка словаря: {e}")
        return ""


def get_json_from_gemini(prompt: str, system_instruction: str = None):
    try:
        logger.info("Проверяю доступные модели...")
        available_models = [m.name for m in client.models.list()]
        target_model = None
        for name in available_models:
            if 'gemini-1.5-flash' in name:
                target_model = name
                break

        if not target_model and available_models:
            target_model = available_models[0]

        if not target_model:
            logger.error("Доступные модели не найдены!")
            return None

        logger.info(f"Использую модель: {target_model}")
        config = {'response_mime_type': 'application/json'}
        if system_instruction:
            config['system_instruction'] = system_instruction

        response = client.models.generate_content(
            model=target_model,
            contents=prompt,
            config=config
        )

        if not response or not response.text:
            return None

        return json.loads(response.text)

    except Exception as e:
        logger.error(f"Ошибка на этапе работы с API: {e}")
        return None


def get_product_analytics(pdf_path: str):
    pages_data = extract_text_from_pdf(pdf_path)
    if not pages_data:
        return None

    ingredients_vocabulary = load_ingredients_dict()
    full_menu_text = ""
    for page_num, content in pages_data:
        clean_lines = [line.strip() for line in content.split('\n') if line.strip()]
        page_text = "\n".join(clean_lines)
        full_menu_text += f"\n--- СТРАНИЦА {page_num} ---\n{page_text}\n"

    logger.info(f"Текст подготовлен. Объем: {len(full_menu_text)} симв.")

    prompt = f"""
    Роль: Экспертный кулинарный аналитик. Преобразуй меню в JSON.
    ИНСТРУМЕНТАРИЙ (Словарь): {ingredients_vocabulary}
    ВЕРНИ СТРОГО JSON:
    {{ "cuisine_type": "...", "total_dishes": 0, "dishes": [ {{ "dish_name": "...", "ingredients": [ {{ "main_ingredient": "...", "attributes": [] }} ] }} ] }}

    МЕНЮ:
    {full_menu_text}
    """
    return prompt


def generate_tips(anya_data: dict, menu_items_list: list = None, months: str = "6-8"):
    cuisine = anya_data.get("cuisine_type", "Азербайджанская")
    total = anya_data.get("total_dishes", 0)

    menu_items_str = ", ".join(menu_items_list) if menu_items_list else "Данные о блюдах отсутствуют"
    system_prompt = f"""
    Роль: Ты — бренд-шеф и гастрономический консультант. Твоя задача — подбор локальных фермерских продуктов для ресторанов.
    Контекст: Мы работаем с рестораном (кухня: {cuisine}, блюд в меню: {total}). 
    Список блюд ресторана: {menu_items_str}.
    Целевой сезон (месяцы): {months}.

    Входящие данные: JSON со списком возможных продуктов.

    Задача: 
    1. Проверь продукты на адекватность целевому сезону.
    2. Отбери лучшие продукты. Идеальный баланс: 7 продуктов типа 'economy' и 8 продуктов типа 'inspiration' (допускается отклонение +-2 продукта).
    3. Для каждого выбранного продукта заполни поле "reason" (150-200 знаков), описывая гастрономическую ценность.

    ВАЖНОЕ ПРАВИЛО (Борьба с галлюцинациями):
    ИСПОЛЬЗУЙ ТОЛЬКО ПРОДУКТЫ ИЗ ПРЕДОСТАВЛЕННОГО JSON! Категорически запрещено выдумывать новые продукты, менять их ID, названия или фермеров. Если во входящем списке меньше 15 продуктов, верни только те, что есть, ничего не добавляя.

    Правила для поля "reason":
    - Для 'economy' (Оптимизация): Укажи 1-2 конкретных блюда из меню, в которых этот продукт можно использовать для снижения себестоимости. Объясни, как он впишется по вкусу.
    - Для 'inspiration' (Вдохновение): Объясни, как этот продукт улучшит или дополнит конкретное блюдо из меню (например: "терпкость этого меда усилит пряность вашего печеного яблока"), либо предложи идею хитового сезонного спешла под эту кухню.
    Ограничение: Верни ответ СТРОГО в формате исходного JSON (список словарей). Оставь только выбранные продукты. Не добавляй markdown-разметку или текст вне JSON.
    """

    user_data_str = json.dumps(anya_data.get("recommendations", []), ensure_ascii=False)

    logger.info("Генерирую глубокую аналитику по промпту Ани...")
    return get_json_from_gemini(user_data_str, system_instruction=system_prompt)

if __name__ == "__main__":
    # Переработка меню из пдф в json
    test_pdf = "Меню 1.pdf"
    print(f"Обрабатываю {test_pdf}...")
    final_prompt = get_product_analytics(test_pdf)

    if final_prompt:
        result = get_json_from_gemini(final_prompt)
        if result:
            print("PDF успешно обработан!")
            with open("menu_result.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4, ensure_ascii=False)

    # в Анин список продуктов добавляются причины
    print("\nПроверяю генерацию советов...")
    example_anya_json = {
        "cuisine_type": "Азербайджанская",
        "total_dishes": 181,
        "recommendations": [
            {
                "product_name": "лисички 0,5 кг.",
                "novelty_score": 100.0,
                "recommendation_type": "inspiration",
                "link": "https://svoe-rodnoe.ru/...",
                "reason": ""
            }
        ]
    }

    tips = generate_tips(example_anya_json)
    if tips:
        print("СОВЕТЫ ПОЛУЧЕНЫ:")
        print(json.dumps(tips, indent=4, ensure_ascii=False))
        print("Советы получены успешно!")
        with open("tips_result.json", "w", encoding="utf-8") as f:
            json.dump(tips, f, indent=4, ensure_ascii=False)
        print("[INFO] Советы сохранены в файл: tips_result.json")
