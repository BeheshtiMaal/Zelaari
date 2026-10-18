import pytest
from fastapi.testclient import TestClient
from server.app import create_app


def test_auth_and_locked_cors() -> None:
    with TestClient(create_app("test-token")) as client:
        assert client.get("/health").status_code == 401
        assert client.get("/health", headers={"Authorization": "Bearer wrong"}).status_code == 401
        headers = {"Authorization": "Bearer test-token"}
        assert client.get("/health", headers=headers).json() == {"status": "ok"}
        response = client.get("/health", headers={**headers, "Origin": "https://evil.invalid"})
        assert "access-control-allow-origin" not in response.headers
        response = client.get("/health", headers={**headers, "Origin": "app://codeharness"})
        assert response.headers["access-control-allow-origin"] == "app://codeharness"


def test_explicit_development_mode_only() -> None:
    with pytest.raises(ValueError):
        create_app("")
    with TestClient(create_app("", dev=True)) as client:
        assert client.get("/health").status_code == 200
