import uuid
import os
import json
from pydantic import BaseModel
from typing import List, Dict, Optional
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from analytics import get_product_analytics, get_json_from_gemini, generate_tips
from business import get_menu_recommendations, get_general_recommendations

app = FastAPI(title="Svoe Chef API")

# подключение фронта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

tasks_db: Dict[str, dict] = {}
UPLOAD_DIR = "temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# для отправки на фронт
class Product(BaseModel):
    product_id: int
    product_name: str
    farmer_name: str
    link: str
    status: str
    novelty_score: float
    season_months: List[int]
    recommendation_type: str
    reason: Optional[str] = None


def run_menu_update_pipeline(task_id: str, file_path: str, start: int, end: int):
    """
    Основная логика обработки:
    1. Юля (LLM) превращает PDF в JSON.
    2. Аня (DB) находит фермерские продукты.
    3. Юля (LLM) пишет финальные советы.
    """
    try:
        tasks_db[task_id]["status"] = "processing"

        # получаем промпт для нейросети на основе текста из PDF
        prompt = get_product_analytics(file_path)
        if not prompt:
            raise Exception("Не удалось извлечь текст из PDF. Возможно, файл пустой.")

        yulia_parsed = get_json_from_gemini(prompt)

        if not yulia_parsed:
            raise Exception("Нет ответа от LLM. Проверьте API-ключ и интернет.")

        # сохранение промежуточного результата в файл
        with open("menu_result.json", "w", encoding="utf-8") as f:
            json.dump(yulia_parsed, f, indent=4, ensure_ascii=False)

        # поиск в базе
        anya_data = get_menu_recommendations("menu_result.json", start, end)

        # генерация советов
        final_result = generate_tips(anya_data)

        if not final_result:
            raise Exception("Ошибка на этапе генерации советов нейросетью.")

        # результат
        tasks_db[task_id]["result"] = final_result
        tasks_db[task_id]["status"] = "completed"

    except Exception as e:
        tasks_db[task_id]["status"] = "error"
        tasks_db[task_id]["error_msg"] = str(e)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# получить меню для анализа
@app.post("/analyze_menu")
async def analyze_menu(
    background_tasks: BackgroundTasks,
    start_month: int,
    end_month: int,
    file: UploadFile = File(...),
):
    task_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{task_id}.pdf")

    with open(file_path, "wb") as f:
        f.write(await file.read())

    tasks_db[task_id] = {"status": "pending"}

    background_tasks.add_task(
        run_menu_update_pipeline, task_id, file_path, start_month, end_month
    )

    return {"task_id": task_id, "message": "Анализ меню запущен"}


# статус обработки меню и результат
@app.get("/status/{task_id}")
async def get_status(task_id: str):
    return tasks_db.get(task_id, {"status": "not_found"})


# вывести список сезонных продуктов
@app.get("/seasonal_dashboard")
async def get_dashboard(start_month: int, end_month: int):
    duration = (end_month - start_month + 12) % 12
    if duration > 2:
        raise HTTPException(
            status_code=400, detail="Период не может превышать 3 месяца"
        )

    return get_general_recommendations(start_month, end_month)


if __name__ == "__main__":
    import uvicorn

    # запуск сервера на локальном хосте
    uvicorn.run(app, host="0.0.0.0", port=8000)
