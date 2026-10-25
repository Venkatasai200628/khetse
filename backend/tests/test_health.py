"""Health endpoint tests."""


def test_health_ok(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["app"] == "KhetSe"
    assert body["demo_mode"] is True


def test_root_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_welcome_is_public_landing_data(client):
    """GET /api/v1/welcome — no auth, gives the app its landing payload."""
    response = client.get("/api/v1/welcome")
    assert response.status_code == 200
    body = response.json()
    assert body["app"] == "KhetSe"
    assert body["tagline"] == "Seedha Khet Se Ghar Tak"
    assert body["demo_mode"] is True


def test_error_shape_on_unknown_route(client):
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body  # FastAPI default 404; AppError shape used for app errors
