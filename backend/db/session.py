from sqlmodel import Session, create_engine
from dotenv import load_dotenv
import os

# Încărcăm variabilele de mediu
load_dotenv()

# Prioritizăm o singură variabilă DATABASE_URL (standard pentru Render/Railway/Supabase)
# Dacă nu există, o construim din bucăți
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DB_USER = os.getenv("user")
    DB_PASSWORD = os.getenv("password")
    DB_HOST = os.getenv("host")
    DB_PORT = os.getenv("port")
    DB_NAME = os.getenv("dbname")
    DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?sslmode=require"

# Ajustări pentru stabilitate în Cloud (Render/Supabase)
# pool_pre_ping=True verifică dacă conexiunea e activă înainte de utilizare
# pool_recycle=300 reînnoiește conexiunile la fiecare 5 minute
engine = create_engine(
    DATABASE_URL, 
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_pre_ping=True,
    pool_recycle=300
)

def get_session():
    """
    Generator de sesiune folosit ca Dependency Injection în rutele FastAPI.
    Se asigură că fiecare request are propria sesiune care se închide automat.
    """
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()