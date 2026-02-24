# Использовать официальный образ Python
FROM python:3.9-slim

# Установить рабочую директорию
WORKDIR /app

# Скопировать файл с зависимостями
COPY requirements.txt .

# Установить зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать код приложения
COPY . .

# Открыть порт, на котором будет работать приложение
EXPOSE 8000

# Команда для запуска приложения
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]