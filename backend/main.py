from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict

# Importăm managerul tău de WebSocket
from core.websocket_manager import manager

app = FastAPI(
    title="RestroManager API",
    description="Backend API for the RestroManager restaurant management system.",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LOGICĂ AI  ---

def run_ai_kds_optimizer(items: List[dict]) -> str:
    """
    AGENT AI 1: Kitchen Optimizer. 
    Analizează complexitatea produselor pentru a sugera prioritizarea.
    """
    # Exemplu: Dacă avem Pizza și Burger, timpul de gătire e mare
    total_prep_expected = sum([item.get("prep_time", 10) for item in items])
    if total_prep_expected > 25:
        return "HIGH_COMPLEXITY - Start Prep Immediately"
    return "STANDARD_PRIORITY"

def run_ai_safety_agent(notes: str) -> str:
    """
    AGENT AI 2: Safety & Urgency Agent.
    Detectează riscuri de sănătate sau solicitări urgente.
    """
    keywords = ["alergie", "allergy", "urgent", "copil", "baby"]
    if any(word in notes.lower() for word in keywords):
        return "CRITICAL"
    return "NORMAL"

# --- 1. Rute de bază ---

@app.get("/")
async def root():
    return {"message": "Welcome to the RestroManager API!"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# --- 2. Rute pentru Comenzi (Legătura cu Dev 1 & Dev 3) ---

@app.post("/api/orders")
async def create_order(order: dict):
    """
    Apelat de Dev 1 (Client). 
    Aici integrăm cei 2 agenți AI înainte de a trimite la KDS.
    """
    # 1. Rulăm agenții AI
    safety_priority = run_ai_safety_agent(order.get("notes", ""))
    cooking_advice = run_ai_kds_optimizer(order.get("items", []))
    
    payload = {
        "event": "NEW_ORDER",
        "ai_metadata": {
            "urgency": safety_priority,
            "cooking_strategy": cooking_advice
        },
        "data": order
    }
    
    # 2. Notificăm Bucătăria (KDS) în timp real
    await manager.broadcast_to_role("chef", payload)
    
    # 3. Notificăm și Chelnerul că s-a ocupat o masă 
    await manager.broadcast_to_role("waiter", {
        "event": "TABLE_OCCUPIED",
        "table": order.get("table_number")
    })

    return {"status": "Processed by AI and sent to KDS", "ai_safety": safety_priority}

# --- 3. WebSockets  ---

@app.websocket("/ws/{role}")
async def websocket_endpoint(websocket: WebSocket, role: str):
    await manager.connect(websocket, role)
    try:
        while True:
            data = await websocket.receive_json()
            
            # ACȚIUNE: Bucătarul marchează comanda ca gata 
            if data.get("action") == "ORDER_READY":
                await manager.broadcast_to_role("waiter", {
                    "event": "FOOD_READY",
                    "table": data.get("table"),
                    "message": f"Mâncarea pentru masa {data.get('table')} este gata de servit!",
                    "type": "success"
                })
                
            # ACȚIUNE: Clientul cheamă chelnerul 
            if data.get("action") == "CALL_WAITER":
                await manager.broadcast_to_role("waiter", {
                    "event": "URGENT_CALL",
                    "table": data.get("table"),
                    "message": "⚠️ Solicitare asistență la masă!"
                })

    except WebSocketDisconnect:
        manager.disconnect(websocket, role)