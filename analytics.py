import logging
import json
import os
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

        # Конфиг оставляем, он правильный
        config = {'response_mime_type': 'application/json', 'temperature': 0.1}
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

    prompt = f"""
    Роль: Экспертный кулинарный аналитик. 
    ЗАДАЧА 1: Оцени, является ли текст МЕНЮ РЕСТОРАНА. Если нет, верни {{"error": "NOT_A_MENU"}}.
    ЗАДАЧА 2: Если это меню, преобразуй в JSON.
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
    menu_items_str = ", ".join(menu_items_list) if menu_items_list else "Данные отсутствуют"

    system_prompt = f"""
    Роль: Бренд-шеф. Контекст: {cuisine} кухня, {total} блюд. Блюда: {menu_items_str}. Сезон: {months}.
    Задача: 
    1. Отбери лучшие продукты из JSON (~7 economy, ~8 inspiration).
    2. Поле "reason": СТРОГО 150-200 знаков. 
    - Economy: использование в блюдах из меню для снижения цены.
    - Inspiration: улучшение блюда из меню или идея спешла.
    ВАЖНО: Только продукты из JSON. Без markdown.
    """

    user_data_str = json.dumps(anya_data.get("recommendations", []), ensure_ascii=False)
    return get_json_from_gemini(user_data_str, system_instruction=system_prompt)


if __name__ == "__main__":
    test_pdf = "Меню 1.pdf"
    print(f"--- [1/2] Обработка PDF: {test_pdf} ---")
    final_prompt = get_product_analytics(test_pdf)

    if final_prompt:
        result = get_json_from_gemini(final_prompt)
        if result and "error" in result:
            print("ОШИБКА: Файл не является меню!")
        elif result:
            print("PDF успешно обработан!")
            with open("menu_result.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4, ensure_ascii=False)

            real_dishes = [d["dish_name"] for d in result.get("dishes", [])]

            print("\n--- [2/2] Генерация советов ---")
            example_anya_json = {
                "cuisine_type": result.get("cuisine_type"),
                "total_dishes": result.get("total_dishes"),
                "recommendations": [
                    {"product_name": "лисички 0,5 кг.", "recommendation_type": "inspiration"},
                    {"product_name": "Баранина лопатка", "recommendation_type": "economy"},
                    {"product_name": "Томаты Бакинские", "recommendation_type": "economy"}
                ]
            }

            tips = generate_tips(example_anya_json, menu_items_list=real_dishes)

            if tips:
                print("СОВЕТЫ ПОЛУЧЕНЫ:")
                print(json.dumps(tips, indent=4, ensure_ascii=False))

                with open("tips_result.json", "w", encoding="utf-8") as f:
                    json.dump(tips, f, indent=4, ensure_ascii=False)
                print(f"Успех! Результаты в tips_result.json")
