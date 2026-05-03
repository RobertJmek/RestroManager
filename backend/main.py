from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importăm ruterele asamblate
from api import api_router
from api.websockets import router as websocket_router

app = FastAPI(
    title="RestroManager API",
    description="Backend API for the RestroManager restaurant management system.",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://restro-manager-app.netlify.app"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. Rutele API Standard (Prefixate cu /api) ---
app.include_router(api_router, prefix="/api")

# --- 2. Rutele WebSocket (Fără prefix, ex: /ws/chef) ---
app.include_router(websocket_router)

# --- 3. Endpoints de Utilitate (Root & Health) ---
@app.get("/")
async def root():
    return {"message": "Welcome to the RestroManager API!"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}