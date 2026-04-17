from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
