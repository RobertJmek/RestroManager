from models.table import Table, TableStatus

def test_table_management_access(client, session):
    # Creăm o masă manual în DB
    table = Table(number=10, capacity=4, status=TableStatus.free)
    session.add(table)
    session.commit()

    # TEST: Un Guest nu ar trebui să poată șterge masa (401/403)
    delete_resp = client.delete(f"/api/tables/{table.id}")
    assert delete_resp.status_code in [401, 403]

    # TEST: Verificăm statusul mesei prin API
    get_resp = client.get(f"/api/tables/{table.number}")
    assert get_resp.json()["status"] == "free"