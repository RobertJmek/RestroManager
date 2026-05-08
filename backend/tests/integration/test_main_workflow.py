from models.category import Category
from models.table import Table, TableStatus
from models.menu_item import MenuItem


def test_complete_customer_journey(client, session):
    # 1. SETUP: Masă, Categorie, Produs
    # conftest mock_get_current_guest returns table_id=1 → table number must be 1
    cat = Category(name="Băuturi")
    session.add(cat)
    table = Table(number=1, capacity=2, status=TableStatus.free)
    session.add(table)
    item = MenuItem(name="Limonadă", price=15.0, category_id=1, is_available=True)
    session.add(item)
    session.commit()

    # 2. CLIENTUL FACE COMANDA (Trigger AI Safety)
    order_payload = {
        "items": [{"menu_item_id": 1, "quantity": 2, "name": "Limonadă", "prep_time": 5}],
        "table_number": 5
    }
    # Simulăm token-ul de Guest scanat la masă
    response = client.post("/api/orders", json=order_payload)
    assert response.status_code == 200
    order_id = response.json()["order_id"]

    # 3. BUCĂTARUL SCHIMBĂ STATUSUL (Integration with Order Logic)
    client.patch(f"/api/orders/{order_id}/status", json={"status": "ready"})

    # 4. CHECKOUT (Eliberare masă)
    checkout_resp = client.post(f"/api/orders/{order_id}/checkout")
    assert checkout_resp.status_code == 200

    # 5. VERIFICARE FINALĂ DB
    session.expire_all()
    assert session.get(Table, table.id).status == TableStatus.free