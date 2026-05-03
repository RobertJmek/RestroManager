from sqlmodel import Session, create_engine
from dotenv import load_dotenv
import os

# Citim variabilele direct din .env 
load_dotenv()

DB_USER = os.getenv("user")
DB_PASSWORD = os.getenv("password")
DB_HOST = os.getenv("host")
DB_PORT = os.getenv("port")
DB_NAME = os.getenv("dbname")

DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"

# DB_ECHO controls SQL query logging. Set to "true" only for local debugging. (M4 fix)
DB_ECHO = os.getenv("DB_ECHO", "false").lower() == "true"

engine = create_engine(DATABASE_URL, echo=DB_ECHO)

def get_session():
    with Session(engine) as session:
        yield session
