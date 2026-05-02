import sys
import os

# Adaugam root-ul in PYTHONPATH pentru a putea importa modulele `backend...`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, SQLModel, select
from db.session import engine
from models.user import User, UserRole
from models.category import Category
from models.table import Table
from models.menu_item import MenuItem
from core.security import get_password_hash

def init_db():
    print("Se creează tabelele în baza de date (dacă nu există deja)...")
    SQLModel.metadata.create_all(engine)

def create_user_if_not_exists(session: Session, name: str, email: str, phone: str, role: UserRole, password: str):
    existing_user = session.exec(select(User).where(User.email == email)).first()
    if existing_user:
        print(f"ℹ️ Utilizatorul {email} există deja. Salt peste...")
        return existing_user
    
    print(f"👤 Se adaugă utilizatorul: {name} ({role})...")
    user = User(
        name=name,
        email=email,
        phone=phone,
        role=role,
        hashed_password=get_password_hash(password),
        is_active=True
    )
    session.add(user)
    return user

def seed_data():
    with Session(engine) as session:
        # 1. Utilizatori
        create_user_if_not_exists(session, "Admin Manager", "manager@restro.com", "+40700111222", UserRole.manager, "manager")
        create_user_if_not_exists(session, "Andrei Waiter", "waiter@restro.com", "+40700333444", UserRole.waiter, "waiter")
        create_user_if_not_exists(session, "Chef Roberto", "chef@restro.com", "+40700555666", UserRole.chef, "chef")
        
        session.commit()

        # 2. Categorii (doar daca nu exista)
        if not session.exec(select(Category)).first():
            print("📁 Se adaugă Categoriile principale...")
            c1 = Category(name="Băuturi", description="Răcoritoare, Cocktailuri și Bere")
            c2 = Category(name="Burgeri", description="Burgeri artizanali din carne de vită Black Angus")
            c3 = Category(name="Pizza", description="Pizza pe vatră, specific napoletan")
            session.add_all([c1, c2, c3])
            session.commit()
            
            # 3. Meniu (doar daca am adaugat categorii noi)
            print("🍔 Se creează Meniul...")
            items = [
                MenuItem(name="Limonadă cu mentă", description="Proaspătă, cu lămâi stoarse", category_id=c1.id, price=17.0, prep_time_minutes=3),
                MenuItem(name="Classic Cheeseburger", description="Chiflă brioche, carne vită, dublu cheddar", category_id=c2.id, price=45.0, prep_time_minutes=15),
                MenuItem(name="Pizza Margherita", description="Sos roșii, mozzarella fior di latte", category_id=c3.id, price=32.0, prep_time_minutes=10),
            ]
            session.add_all(items)
        else:
            print("ℹ️ Categoriile există deja. Salt peste meniu...")

        # 4. Mese (doar daca nu exista)
        if not session.exec(select(Table)).first():
            print("🪑 Se adaugă Mesele...")
            tables = [
                Table(number=1, capacity=4, location="Lângă Geam"),
                Table(number=2, capacity=2, location="Terasă"),
                Table(number=3, capacity=4, location="Terasă"),
            ]
            session.add_all(tables)
        else:
            print("ℹ️ Mesele există deja. Salt peste...")

        session.commit()
        print("✅ Succes! Datele au fost actualizate.")

if __name__ == "__main__":
    init_db()
    seed_data()
