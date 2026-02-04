import uuid


def test_tenant_required_missing_client_id(app):
    client = app.test_client()

    response = client.get("/health/tenant")

    assert response.status_code == 400
    assert response.get_json()["message"] == "client_id is required for this resource."


def test_tenant_header_sets_client_id(app):
    app.config["ALLOW_X_CLIENT_ID_HEADER"] = True
    client = app.test_client()
    client_id = str(uuid.uuid4())

    response = client.get("/health/tenant", headers={"X-Client-Id": client_id})

    assert response.status_code == 200
    assert response.get_json() == {"client_id": client_id}


def test_invalid_client_id_returns_bad_request(app):
    app.config["ALLOW_X_CLIENT_ID_HEADER"] = True
    client = app.test_client()

    response = client.get("/health/tenant", headers={"X-Client-Id": "not-a-uuid"})

    assert response.status_code == 400
    assert response.get_json()["message"] == "Invalid client_id format."
