from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from student_workbench.config import AppConfig
from student_workbench.main import create_app

WEB_HEADERS = {
    "Origin": "http://127.0.0.1:5173",
    "X-Student-Workbench-Client": "web",
}


@pytest.fixture
def app(tmp_path):
    config = AppConfig(
        data_dir=tmp_path,
        db_url=f"sqlite:///{tmp_path / 'test.db'}",
    )
    return create_app(config)


@pytest.fixture
def client(app):
    with TestClient(app, headers=WEB_HEADERS) as test_client:
        yield test_client


@pytest.fixture
def raw_client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def session_factory(app):
    return app.state.session_factory
