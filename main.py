import uuid
import os
import json
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from analytics import (
    get_product_analytics_prompt,
    call_gemini_api,
    generate_expert_tips,
)
from business import get_menu_recommendations, get_general_recommendations

UPLOAD_DIR = "temp_uploads"  # папка для временного хранения pdf
MENU_RESULT_FILE = "menu_result.json"
MAX_SEASONAL_MONTHS = 3
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000
ERROR_NOT_A_MENU = "NOT_A_MENU"

app = FastAPI(title="Svoe Chef API")

# настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


tasks_db: Dict[str, Dict[str, Any]] = {}  # сохраняем статус процесса анализа меню

os.makedirs(UPLOAD_DIR, exist_ok=True)


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


def save_json_file(data: Any, file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def run_menu(task_id: str, file_path: str, start: int, end: int) -> None:
    try:
        tasks_db[task_id]["status"] = "processing"

        # парсинг pdf
        analysis_prompt = get_product_analytics_prompt(file_path)
        if not analysis_prompt:
            raise Exception("Ошибка при извлечении текста из файла")

        parsed_menu = call_gemini_api(analysis_prompt)
        if not parsed_menu:
            raise Exception("Нейросеть не смогла разобрать меню")

        # eсли это не меню, сразу возвращаем ошибку
        if parsed_menu.get("error") == ERROR_NOT_A_MENU:
            tasks_db[task_id]["result"] = parsed_menu
            tasks_db[task_id]["status"] = "completed"
            return

        save_json_file(parsed_menu, MENU_RESULT_FILE)

        # ищем подходящие фермерские продукты в базе данных
        recommendations = get_menu_recommendations(MENU_RESULT_FILE, start, end)

        # получаем совет по обновлению меню
        final_result = generate_expert_tips(recommendations)
        if not final_result:
            raise Exception("Ошибка при генерации финальных советов")

        tasks_db[task_id]["result"] = final_result
        tasks_db[task_id]["status"] = "completed"

    except Exception as e:
        tasks_db[task_id]["status"] = "error"
        tasks_db[task_id]["error_msg"] = str(e)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@app.post("/analyze_menu")
async def analyze_menu(
    background_tasks: BackgroundTasks,
    start_month: int,
    end_month: int,
    file: UploadFile = File(...),
) -> Dict[str, str]:
    task_id = str(uuid.uuid4())
    temp_path = os.path.join(UPLOAD_DIR, f"{task_id}.pdf")

    with open(temp_path, "wb") as f:
        f.write(await file.read())

    tasks_db[task_id] = {"status": "pending"}
    background_tasks.add_task(run_menu, task_id, temp_path, start_month, end_month)

    return {"task_id": task_id, "message": "Анализируем меню"}


@app.get("/status/{task_id}")
async def get_task_status(task_id: str) -> Dict[str, Any]:
    return tasks_db.get(task_id, {"status": "not_found"})


@app.get("/seasonal_dashboard")
async def get_seasonal_dashboard(start_month: int, end_month: int) -> List[Any]:
    duration = (end_month - start_month + 12) % 12
    if duration >= MAX_SEASONAL_MONTHS:
        raise HTTPException(
            status_code=400,
            detail=f"Период анализа не может превышать {MAX_SEASONAL_MONTHS} месяца",
        )

    return get_general_recommendations(start_month, end_month)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)

