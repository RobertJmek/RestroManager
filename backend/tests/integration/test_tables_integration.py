from models.table import Table, TableStatus

def test_table_management_access(client, session):
    # Creăm o masă manual în DB
    table = Table(number=10, capacity=4, status=TableStatus.free)
    session.add(table)
    session.commit()

    # TEST: Un Guest nu ar trebui să poată șterge masa (401/403/404/405)
    delete_resp = client.delete(f"/api/tables/{table.id}")
    assert delete_resp.status_code in [401, 403, 404, 405]

    # TEST: Verificăm statusul mesei direct în DB
    session.refresh(table)
    assert table.status == TableStatus.free