import logging
import json
from pdf_extractor import extract_text_from_pdf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_ingredients_dict(file_path: str = "ingredients_list_for_yulia.txt") -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"Словарь ингредиентов успешно загружен из {file_path}")
            return content
    except FileNotFoundError:
        logger.error(f"Файл словаря {file_path} не найден!")
        return ""
    except Exception as e:
        logger.error(f"Ошибка при загрузке словаря: {e}")
        return ""


def get_product_analytics(pdf_path: str):
    pages_data = extract_text_from_pdf(pdf_path)
    if not pages_data:
        logger.error("Данные из PDF не получены.")
        return None

    ingredients_vocabulary = load_ingredients_dict()

    full_menu_text = ""
    for page_num, content in pages_data:
        full_menu_text += f"\n--- СТРАНИЦА {page_num} ---\n{content}\n"

# промт...
    prompt = f"""
    Роль: Экспертный кулинарный аналитик. Преобразуй меню в JSON.

    ИНСТРУМЕНТАРИЙ (Словарь доступных продуктов):
    {ingredients_vocabulary}

    ПРАВИЛА:
    1. Определи тип кухни (cuisine_type).
    2. main_ingredient: только существительное, ед. число, им. падеж. Сверяй со словарем!
    3. attributes: массив прилагательных (свойства, обработка).
    4. Если продукта нет в словаре — нормализуй и запиши всё равно.

    ФОРМАТ ОТВЕТА (JSON):
    {{
      "cuisine_type": "...",
      "dishes": [
        {{
          "dish_name": "...",
          "ingredients": [
            {{ "main_ingredient": "...", "attributes": [] }}
          ]
        }}
      ]
    }}

    МЕНЮ ДЛЯ АНАЛИЗА:
    {full_menu_text}
    """

    return prompt


if __name__ == "__main__":
    test_pdf = "Меню 1.pdf"
    final_prompt = get_product_analytics(test_pdf)

    if final_prompt:
        print("ПРОМПТ ДЛЯ НЕЙРОНКИ СФОРМИРОВАН:")
        print(final_prompt[:1000] + "...")
