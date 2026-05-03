# Folosim o imagine oficială și optimizată de Python 3.12
FROM python:3.12-slim

# Setăm folderul de lucru în container unde vom copia fișierele
WORKDIR /app

# Copiem DOAR requirements.txt mai întâi pentru a beneficia de caching-ul de layere din Docker
# Asta face ca rebuild-ul imaginii să fie mult mai rapid dacă nu se schimbă pachetele
COPY backend/requirements.txt ./backend/requirements.txt

# Instalăm dependențele și curățăm cache-ul (pentru o imagine mai mică)
RUN pip install --no-cache-dir -r backend/requirements.txt

# Acum copiem restul codului din backend în folderul /app/backend
COPY backend/ ./backend/

# Setăm variabile de mediu utile pt Python în containere Docker
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/backend

# Expunem portul pe care va rula aplicația FastAPI
EXPOSE 8000

# Comanda care va rula la pornirea containerului
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
