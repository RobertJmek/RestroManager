from models.category import Category
from models.table import Table, TableStatus
from models.menu_item import MenuItem
from core.security import create_access_token

# Helper to create a guest token
def create_guest_token(table_id: int = 1):
    return create_access_token(
        data={"role": "Guest", "table_id": table_id}
    )

def test_complete_customer_journey(client, session, chef_headers, waiter_headers):
    # 1. SETUP: Masă, Categorie, Produs
    cat = Category(name="Băuturi")
    session.add(cat)
    table = Table(number=1, capacity=2, status=TableStatus.free)
    session.add(table)
    item = MenuItem(name="Limonadă", price=15.0, category_id=1, is_available=True)
    session.add(item)
    session.commit()

    # 2. CLIENTUL FACE COMANDA (Trigger AI Safety)
    order_payload = {
        "items": [{"menu_item_id": 1, "quantity": 2, "name": "Limonadă", "prep_time": 5}]
    }
    # Simulăm token-ul de Guest scanat la masă
    token = create_guest_token(table_id=1)
    response = client.post(
        "/api/orders", 
        json=order_payload,
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    order_id = response.json()["order_id"]

    # 3. BUCĂTARUL SCHIMBĂ STATUSUL (Integration with Order Logic)
    status_resp = client.patch(
        f"/api/orders/{order_id}/status", json={"status": "ready"}, headers=chef_headers
    )
    assert status_resp.status_code == 200

    # 4. CHECKOUT (Eliberare masă — Chelnerul autentificat)
    checkout_resp = client.post(f"/api/orders/{order_id}/checkout", headers=waiter_headers)
    assert checkout_resp.status_code == 200

    # 5. VERIFICARE FINALĂ DB
    session.expire_all()
    assert session.get(Table, table.id).status == TableStatus.free