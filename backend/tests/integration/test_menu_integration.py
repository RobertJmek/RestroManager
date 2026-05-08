from models.category import Category
from models.menu_item import MenuItem

def test_full_menu_lifecycle(client, session):
    # 1. Creare Categorie direct în DB (Manager-only endpoint, bypass auth)
    cat = Category(name="Paste")
    session.add(cat)
    session.commit()
    session.refresh(cat)

    # 2. Adăugare Produs direct în DB
    item = MenuItem(name="Pasta Carbonara", price=40.0, category_id=cat.id, is_available=True, prep_time_minutes=15)
    session.add(item)
    session.commit()

    # 3. Validare vizibilitate publică (Guest view via API)
    get_resp = client.get("/api/menu")
    assert get_resp.status_code == 200
    assert any(i["name"] == "Pasta Carbonara" for i in get_resp.json())