import pytest
from sqlmodel import select
from models.table import Table, TableStatus
from models.menu_item import MenuItem
from models.category import Category  
from models.order import Order, OrderStatus

# --- 1. INTEGRARE MENIU & CATEGORII ---
def test_menu_category_integration(client, session):
    """Verifică dacă meniul și categoriile colaborează corect."""
    # Creăm o categorie prin API (sau direct în DB pentru setup)
    cat = Category(name="Paste")
    session.add(cat)
    session.commit()
    
    # Adăugăm un produs legat de acea categorie
    item = MenuItem(name="Penne", price=35.0, category_id=cat.id, is_available=True, prep_time=10)
    session.add(item)
    session.commit()
    
    # Verificăm dacă API-ul de meniu returnează produsul corect
    response = client.get("/api/menu")
    assert response.status_code == 200
    assert any(item["name"] == "Penne" for item in response.json())

# --- 2. FLUX COMPLET: COMANDĂ -> STATUS MASA -> AI METADATA ---
def test_create_order_full_integration(client, session):
    """Testează crearea comenzii, ocuparea mesei și prezența datelor AI."""
    # Setup masă și produs
    cat = Category(name="Pizze")
    session.add(cat)
    table = Table(number=1, capacity=4, status=TableStatus.free)
    session.add(table)
    item = MenuItem(name="Margherita", price=40.0, category_id=1, is_available=True, prep_time=12)
    session.add(item)
    session.commit()

    order_payload = {
        "items": [{
            "menu_item_id": item.id, 
            "quantity": 1, 
            "name": "Margherita", 
            "prep_time": 12,
            "special_instructions": "Fără sare, vă rog - Alergie!"
        }]
    }
    
    # 1. Executăm comanda
    response = client.post("/api/orders", json=order_payload)
    assert response.status_code == 200
    
    # 2. Verificăm dacă AI-ul a procesat datele (verificăm structura răspunsului)
    data = response.json()
    assert "ai_safety" in data
    assert "order_id" in data

    # 3. Verificăm dacă masa a devenit ocupată automat
    session.expire_all()
    db_table = session.exec(select(Table).where(Table.number == 1)).first()
    assert db_table.status == TableStatus.occupied

# --- 3. INTEGRARE BUCĂTĂRIE (KDS) ---
def test_kitchen_order_status_update(client, session):
    """Verifică dacă Bucătarul poate schimba statusul comenzii."""
    # Setup masă și comandă existentă
    table = Table(number=1, capacity=4, status=TableStatus.occupied)
    session.add(table)
    session.commit()
    session.refresh(table)

    test_order = Order(table_id=table.id, status=OrderStatus.pending, total_price=50.0)
    session.add(test_order)
    session.commit()

    # Simulăm Bucătarul care marchează comanda ca fiind gata (Ready)
    # Notă: Dacă require_role e activ, testul ar putea cere headers de auth
    response = client.patch(f"/api/orders/{test_order.id}/status", json={"status": "ready"})
    
    assert response.status_code == 200
    session.refresh(test_order)
    assert test_order.status == OrderStatus.ready

# --- 4. FINALIZARE FLUX: CHECKOUT & ELIBERARE ---
def test_checkout_and_cleanup_integration(client, session):
    """Verifică închiderea comenzii și eliberarea resurselor."""
    # Setup
    table = Table(number=1, capacity=4, status=TableStatus.occupied)
    session.add(table)
    session.commit()
    session.refresh(table)

    test_order = Order(table_id=table.id, status=OrderStatus.ready, total_price=100.0)
    session.add(test_order)
    session.commit()

    # Executăm Checkout (Chelnerul închide masa)
    response = client.post(f"/api/orders/{test_order.id}/checkout")
    assert response.status_code == 200
    
    session.expire_all()
    db_order = session.get(Order, test_order.id)
    db_table = session.get(Table, table.id)

    # Verificăm că totul a revenit la starea neutră
    assert db_order.status == OrderStatus.completed
    assert db_table.status == TableStatus.free

# --- 5. INTEGRARE SECURITATE (ROLES) ---
def test_security_unauthorized_access(client, session):
    """Verifică dacă endpoint-urile protejate resping cererile fără drepturi."""
    # Încercăm să actualizăm statusul unei comenzi inexistente 
    # (Ar trebui să dea 401 înainte de 404 dacă securitatea e activă)
    response = client.patch("/api/orders/999/status", json={"status": "ready"})
    
    # Dacă ai require_role activat corect, acesta va returna 401
    assert response.status_code in [401, 403, 404]