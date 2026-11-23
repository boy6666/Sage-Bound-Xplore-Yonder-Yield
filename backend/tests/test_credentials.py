from __future__ import annotations

from sqlalchemy import text

from student_workbench.services import credentials
from tests.helpers import create_connection


def test_save_password_uses_keyring_only(client, session_factory, monkeypatch):
    calls = []

    def fake_set_password(service, key, value):
        calls.append((service, key, value))

    monkeypatch.setattr(credentials.keyring, "set_password", fake_set_password)

    connection = create_connection(client)
    response = client.post(
        f"/api/v1/connections/{connection['id']}/login",
        json={"username": "demo", "password": "super-secret-pw", "save_password": True},
    )
    assert response.status_code == 200, response.text

    assert calls == [
        ("student-workbench", f"platform:{connection['id']}", "super-secret-pw")
    ]

    listed = client.get("/api/v1/connections").json()["items"][0]
    assert listed["credential_saved"] is True

    with session_factory() as session:
        rows = session.execute(text("select * from connections")).mappings().all()
    assert rows
    assert "super-secret-pw" not in str(rows)
    assert "super-secret-pw" not in str(client.get("/api/v1/settings").json())


def test_login_without_saving_does_not_touch_keyring(client, monkeypatch):
    calls = []

    def fake_set_password(service, key, value):
        calls.append((service, key, value))

    monkeypatch.setattr(credentials.keyring, "set_password", fake_set_password)

    connection = create_connection(client)
    response = client.post(
        f"/api/v1/connections/{connection['id']}/login",
        json={"username": "demo", "password": "pw", "save_password": False},
    )
    assert response.status_code == 200
    assert calls == []
    assert client.get("/api/v1/connections").json()["items"][0]["credential_saved"] is False


def test_keyring_failure_does_not_store_flag(client, monkeypatch):
    def boom(service, key, value):
        raise RuntimeError("no keyring backend")

    monkeypatch.setattr(credentials.keyring, "set_password", boom)

    connection = create_connection(client)
    response = client.post(
        f"/api/v1/connections/{connection['id']}/login",
        json={"username": "demo", "password": "pw", "save_password": True},
    )
    assert response.status_code == 200
    assert client.get("/api/v1/connections").json()["items"][0]["credential_saved"] is False
