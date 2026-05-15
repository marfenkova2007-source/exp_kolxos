// Если запускаешь всё на одном компьютере, адрес будет таким:
const BASE_URL = "http://localhost:8000";

export const ApiService = {
    /**
     * 1. ПОЛУЧЕНИЕ КАТАЛОГА (БЕЗ АНАЛИЗА)
     * Используется для простого отображения продуктов за выбранные месяцы.
     */
    async getSeasonalDashboard(startMonth, endMonth) {
        try {
            const response = await fetch(`${BASE_URL}/seasonal_dashboard?start_month=${startMonth}&end_month=${endMonth}`);

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || "Ошибка при загрузке каталога");
            }

            return await response.json();
        } catch (err) {
            console.error("API Error (getSeasonalDashboard):", err);
            throw err;
        }
    },

    /**
     * 2. ЗАПУСК АНАЛИЗА МЕНЮ (ЗАГРУЗКА PDF)
     * Отправляет файл и возвращает task_id для отслеживания.
     */
    async uploadMenuForAnalysis(file, startMonth, endMonth) {
        try {
            const formData = new FormData();
            formData.append('file', file); // Ключ 'file' строго как в бэкенде

            const url = `${BASE_URL}/analyze_menu?start_month=${startMonth}&end_month=${endMonth}`;
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) throw new Error("Не удалось отправить файл на анализ");

            return await response.json(); // Вернет { "task_id": "...", "message": "..." }
        } catch (err) {
            console.error("API Error (uploadMenuForAnalysis):", err);
            throw err;
        }
    },

    /**
     * 3. ПРОВЕРКА СТАТУСА ЗАДАЧИ (POLLING)
     * Нужно вызывать по таймеру, пока статус не станет 'completed'.
     */
    async getTaskStatus(taskId) {
        try {
            const response = await fetch(`${BASE_URL}/status/${taskId}`);
            if (!response.ok) throw new Error("Ошибка при проверке статуса");

            return await response.json();
            // Вернет { "status": "pending" | "processing" | "completed" | "error", "result": [...] }
        } catch (err) {
            console.error("API Error (getTaskStatus):", err);
            throw err;
        }
    }
};