import logging
import json
from google import genai
from pdf_extractor import extract_text_from_pdf

GOOGLE_API_KEY = "AIzaSyCQmX9xBRMFOdLXcGn6m0fVQRlSG6r2URI"
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


def get_json_from_gemini(prompt: str):
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

        response = client.models.generate_content(
            model=target_model,
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
            }
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
    {{ "cuisine_type": "...", "dishes": [ {{ "dish_name": "...", "ingredients": [ {{ "main_ingredient": "...", "attributes": [] }} ] }} ] }}

    МЕНЮ:
    {full_menu_text}
    """
    return prompt


if __name__ == "__main__":
    test_pdf = "Меню 1.pdf"
    final_prompt = get_product_analytics(test_pdf)

    if final_prompt:
        result = get_json_from_gemini(final_prompt)

        if result:
            print("\n" + "=" * 50)
            print("ПОБЕДА! JSON ПОЛУЧЕН:")
            print(json.dumps(result, indent=4, ensure_ascii=False))
            print("=" * 50)

            output_file = "menu_result.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4, ensure_ascii=False)

            print(f"\n[INFO] Данные успешно сохранены в файл: {output_file}")
        else:
            print("Не удалось получить результат от нейронки.")
