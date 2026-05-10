import pdfplumber
import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> list:
    full_text = []

    try:
        with pdfplumber.open(pdf_path) as pdf:
            logger.info(f"Начинаю извлечение текста из: {pdf_path}")
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text(
                    layout=True,  # Пытается сохранить визуальное расположение текста
                    use_text_flow=True
                )

                if page_text:
                    full_text.append([i+1, page_text])
                else:
                    logger.warning(f"Страница {i + 1} кажется пустой") # пока идейно заставить LLM её перепроверить

        all_text_combined = ""
        for page_data in full_text:
            page_content = page_data[1]
            all_text_combined += page_content + "\n"

        total_symbols = len(all_text_combined)
        logger.info(f"Итого собрано символов: {total_symbols}")
        return full_text


    except Exception as e:
        logger.error(f"Ошибка при чтении PDF {pdf_path}: {e}")
        return []



if __name__ == "__main__":
    test_pdf = "Меню 1"
    pages_data = extract_text_from_pdf(test_pdf)

    if pages_data:
        print(f"Успешно извлечено страниц: {len(pages_data)}")
        # Берем текст только первой страницы [0] и её содержимое [1]
        first_page_text = pages_data[0][1]
        print("-" * 30)
        print(first_page_text[:500])
        print("-" * 30)
    else:
        print("Список пуст. Проверь логи (logger.error).")
