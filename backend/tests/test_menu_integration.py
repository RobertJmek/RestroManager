from models.category import Category
from models.menu_item import MenuItem

def test_full_menu_lifecycle(client, session):
    # 1. Creare Categorie
    cat_resp = client.post("/api/categories/", json={"name": "Paste"})
    assert cat_resp.status_code == 201
    cat_id = cat_resp.json()["id"]

    # 2. Adăugare Produs în Categorie
    item_data = {
        "name": "Pasta Carbonara",
        "price": 40.0,
        "category_id": cat_id,
        "is_available": True,
        "prep_time": 15
    }
    item_resp = client.post("/api/menu/items", json=item_data)
    assert item_resp.status_code == 201

    # 3. Validare vizibilitate publică (Guest view)
    get_resp = client.get("/api/menu")
    assert any(i["name"] == "Pasta Carbonara" for i in get_resp.json())