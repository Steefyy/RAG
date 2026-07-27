FROM python:3.12-slim

WORKDIR /app

# Instalam dependintele
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiem codul sursa al aplicatiei
COPY . .

# Expunem portul FastAPI
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
