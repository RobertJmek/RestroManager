from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.websocket_manager import manager
from fastapi import WebSocket, WebSocketDisconnect

app = FastAPI(
    title="RestroManager API",
    description="Backend API for the RestroManager restaurant management system.",
    version="1.0.0",
)

# Configure CORS for decoupled frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production to match your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to the RestroManager API!"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.websocket("/ws/{role}")
async def websocket_endpoint(websocket: WebSocket, role: str):
    await manager.connect(websocket, role)
    try:
        while True:
            # We are waiting for messages (ex: The customer calls the waiter)
            data = await websocket.receive_json()
            # Here we will insert the call to the AI ​​AGENT later
            await manager.broadcast_to_role("waiter", {"event": "call_waiter", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket, role)