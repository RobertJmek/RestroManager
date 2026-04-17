

##### NU MAI TREBUIE DAT SEED PE BAZA NOASTRA DE DATE PENTRU CA AM DAT EU DEJA, SI E IN CLOUD !!!!


import sys
import os

# Adaugam root-ul in PYTHONPATH pentru a putea importa modulele `backend...`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, SQLModel
from backend.db.session import engine
from backend.models.user import User, UserRole
from backend.models.category import Category
from backend.models.table import Table, TableStatus
from backend.models.menu_item import MenuItem

def init_db():
    print("Se creează tabelele în baza de date (dacă nu există deja)...")
    SQLModel.metadata.create_all(engine)

def seed_data():
    with Session(engine) as session:
        # Verificăm dacă avem deja date pentru a evita un crash de tip `unique constraint`
        existing_manager = session.query(User).filter(User.email == "manager@restro.com").first()
        if existing_manager:
            print("❌ Datele există deja în baza de date! Scriptul a fost oprit pentru a nu duplica intrările.")
            return

        print("👨‍💼 Se adaugă contul de Manager...")
        manager = User(
            name="Ion Popescu (Manager)",
            email="manager@restro.com",
            phone="+40700111222",
            role=UserRole.manager,
            hashed_password="placeholder_hash_parola", # În producție vom folosi Passlib/Bcrypt
            is_active=True
        )
        session.add(manager)

        print("📁 Se adaugă Categoriile principare...")
        # Trebuie să obținem id-urile categoriilor, deci dăm flush/commit imediat
        c1 = Category(name="Băuturi", description="Răcoritoare, Cocktailuri și Bere")
        c2 = Category(name="Burgeri", description="Burgeri artizanali din carne de vită Black Angus")
        c3 = Category(name="Pizza", description="Pizza pe vatră, specific napoletan")
        session.add_all([c1, c2, c3])
        session.commit()

        print("🍔 Se creează Meniul (10 produse)...")
        items = [
            # Bauturi
            MenuItem(name="Limonadă cu mentă", description="Proaspătă, cu lămâi stoarse", category_id=c1.id, price=17.0, prep_time_minutes=3),
            MenuItem(name="Coca Cola", description="Doză 330ml", category_id=c1.id, price=10.0, prep_time_minutes=1),
            MenuItem(name="Ursus Premium", description="Bere blondă 500ml draught", category_id=c1.id, price=12.0, prep_time_minutes=2),
            
            # Burgeri
            MenuItem(name="Classic Cheeseburger", description="Chiflă brioche, carne vită, dublu cheddar, castraveți, sos", category_id=c2.id, price=45.0, prep_time_minutes=15),
            MenuItem(name="Spicy Bacon Burger", description="Carne vită, bacon crispy, sos jalapeno, ceapă prăjită", category_id=c2.id, price=52.0, prep_time_minutes=15),
            MenuItem(name="Truffle Mushroom Burger", description="Carne vită, maioneză cu trufe, ciuperci", category_id=c2.id, price=55.0, prep_time_minutes=18),
            
            # Pizza
            MenuItem(name="Pizza Margherita", description="Sos de roșii San Marzano, mozzarella fior di latte", category_id=c3.id, price=32.0, prep_time_minutes=10, dietary_tags="Vegetarian"),
            MenuItem(name="Pizza Diavola", description="Sos de roșii, mozzarella, salam picant", category_id=c3.id, price=40.0, prep_time_minutes=12, dietary_tags="Picant"),
            MenuItem(name="Pizza Quattro Formaggi", description="Mozzarella, gorgonzola, ementaler, parmezan", category_id=c3.id, price=42.0, prep_time_minutes=12, dietary_tags="Vegetarian"),
            MenuItem(name="Pizza Prosciutto e Funghi", description="Sos de roșii, mozzarella, șuncă, ciuperci", category_id=c3.id, price=38.0, prep_time_minutes=12),
        ]
        session.add_all(items)

        print("🪑 Se orchestrează Mesele...")
        tables = [
            Table(number=1, capacity=4, location="Lângă Geam"),
            Table(number=2, capacity=2, location="Terasă"),
            Table(number=3, capacity=4, location="Terasă"),
            Table(number=4, capacity=6, location="Centru"),
            Table(number=5, capacity=2, location="Separeu"),
        ]
        session.add_all(tables)

        # Commit final pentru toate insertiile rămase
        session.commit()
        print("✅ Success! Baza de date a fost populată cu datele de start.")

if __name__ == "__main__":
    init_db()
    seed_data()
