from __future__ import annotations

from tests.helpers import (
    create_connection,
    create_work_item,
    identity_by_name,
    login_ready,
    unmatched_identities,
)


def _sync(client, connection_id):
    response = client.post(f"/api/v1/connections/{connection_id}/sync")
    assert response.status_code == 202, response.text
    run = client.get(f"/api/v1/sync-runs/{response.json()['sync_run_id']}")
    assert run.status_code == 200
    return run.json()


def _academic_connection(client):
    connection = create_connection(
        client, kind="academic", provider="academic_fake", name="教务（示例）"
    )
    login_ready(client, connection["id"], username="student", password="pw")
    _sync(client, connection["id"])
    return connection


def _learning_connection(client):
    connection = create_connection(
        client, kind="learning", provider="learning_fake", name="学习通（示例）"
    )
    login_ready(client, connection["id"], username="demo", password="pw")
    _sync(client, connection["id"])
    return connection


def test_create_course(client):
    response = client.post(
        "/api/v1/courses",
        json={"name": "操作系统", "code": "CS301", "term": "2026-2027-1", "teacher": "张老师"},
    )
    assert response.status_code == 201, response.text
    course = response.json()
    assert course["name"] == "操作系统"
    assert course["code"] == "CS301"
    assert course["identities"] == []
    assert course["open_todos"] == 0
    assert course["next_class"] is None


def test_same_name_different_term_is_not_merged(client):
    first = client.post(
        "/api/v1/courses", json={"name": "操作系统", "term": "2025-2026-2"}
    ).json()
    second = client.post(
        "/api/v1/courses", json={"name": "操作系统", "term": "2026-2027-1"}
    ).json()
    assert first["id"] != second["id"]
    courses = client.get("/api/v1/courses").json()["items"]
    assert len(courses) == 2


def test_course_detail_shape(client):
    course = client.post(
        "/api/v1/courses", json={"name": "操作系统", "term": "2026-2027-1"}
    ).json()
    create_work_item(client, title="作业", course_id=course["id"], status="inbox")
    create_work_item(client, title="已完成", course_id=course["id"], status="done")

    detail = client.get(f"/api/v1/courses/{course['id']}").json()
    assert set(detail) == {"course", "schedule", "todos"}
    assert [item["title"] for item in detail["todos"]] == ["作业"]
    assert detail["course"]["open_todos"] == 1


def test_schedule_missing_term_start(client):
    course = client.post(
        "/api/v1/courses", json={"name": "操作系统", "term": "2026-2027-1"}
    ).json()
    _ = course
    response = client.get("/api/v1/courses/schedule")
    assert response.status_code == 200
    body = response.json()
    assert body["missing_term_start"] is True
    assert body["term_start_date"] is None
    assert body["current_week"] is None
    assert body["entries"] == []


def test_academic_sync_creates_identities_and_schedule(client):
    _academic_connection(client)
    entries = unmatched_identities(client)
    assert {entry["identity"]["external_name"] for entry in entries} == {
        "操作系统",
        "数据库原理",
    }
    assert all(entry["provider"] == "academic_fake" for entry in entries)

    course = client.post(
        "/api/v1/courses",
        json={"name": "操作系统", "code": "CS301", "term": "2026-2027-1", "teacher": "张老师"},
    ).json()
    identity = identity_by_name(client, "操作系统")["identity"]
    link = client.post(
        f"/api/v1/course-identities/{identity['id']}/link",
        json={"course_id": course["id"]},
    )
    assert link.status_code == 200, link.text
    assert link.json()["match_status"] == "manual"
    assert link.json()["course_id"] == course["id"]

    detail = client.get(f"/api/v1/courses/{course['id']}").json()
    assert len(detail["schedule"]) == 1
    entry = detail["schedule"][0]
    assert entry["weekday"] == 1
    assert entry["start_time"] == "08:00"
    assert entry["end_time"] == "09:40"
    assert entry["location"] == "教三-201"
    assert entry["course_id"] == course["id"]
    assert entry["course_name"] == "操作系统"
    assert entry["weeks"][:3] == [1, 2, 3]
    assert entry["weeks_label"] == "1-16周"

    remaining = {entry["identity"]["external_name"] for entry in unmatched_identities(client)}
    assert remaining == {"数据库原理"}


def test_schedule_endpoint_with_term_start_and_week_filter(client):
    client.patch("/api/v1/settings", json={"term_start_date": "2026-09-01"})
    _academic_connection(client)
    course = client.post(
        "/api/v1/courses", json={"name": "操作系统", "term": "2026-2027-1"}
    ).json()
    identity = identity_by_name(client, "操作系统")["identity"]
    client.post(
        f"/api/v1/course-identities/{identity['id']}/link",
        json={"course_id": course["id"]},
    )

    body = client.get("/api/v1/courses/schedule", params={"week": 12}).json()
    assert body["missing_term_start"] is False
    assert body["term_start_date"] == "2026-09-01"
    assert len(body["entries"]) == 1

    empty = client.get("/api/v1/courses/schedule", params={"week": 20}).json()
    assert empty["entries"] == []


def test_unmatched_suggestions_prefer_exact_name(client):
    _learning_connection(client)
    course = client.post(
        "/api/v1/courses", json={"name": "数据库原理", "term": "2026-2027-1"}
    ).json()
    entry = identity_by_name(client, "数据库原理")
    suggestions = entry["suggested"]
    assert [item["course_id"] for item in suggestions] == [course["id"]]
    assert suggestions[0]["reason"]


def test_link_rebinds_learning_work_items_and_schedule(client):
    _academic_connection(client)
    _learning_connection(client)
    course = client.post(
        "/api/v1/courses", json={"name": "操作系统", "term": "2026-2027-1", "teacher": "张老师"}
    ).json()

    academic_identity = identity_by_name(client, "操作系统")["identity"]
    client.post(
        f"/api/v1/course-identities/{academic_identity['id']}/link",
        json={"course_id": course["id"]},
    )
    learning_identity = identity_by_name(client, "操作系统")["identity"]
    response = client.post(
        f"/api/v1/course-identities/{learning_identity['id']}/link",
        json={"course_id": course["id"]},
    )
    assert response.status_code == 200

    linked = client.get("/api/v1/work-items", params={"course_id": course["id"]}).json()
    assert {item["title"] for item in linked["items"]} == {
        "操作系统实验二",
        "操作系统实验一",
        "操作系统实验零",
    }

    detail = client.get(f"/api/v1/courses/{course['id']}").json()
    assert len(detail["schedule"]) == 1
    assert detail["course"]["open_todos"] == 2


def test_unlink_keeps_work_items_but_clears_course(client):
    _learning_connection(client)
    course = client.post(
        "/api/v1/courses", json={"name": "操作系统", "term": "2026-2027-1"}
    ).json()
    identity = identity_by_name(client, "操作系统")["identity"]
    client.post(
        f"/api/v1/course-identities/{identity['id']}/link",
        json={"course_id": course["id"]},
    )
    before = len(client.get("/api/v1/work-items").json()["items"])
    assert before == 4

    response = client.post(f"/api/v1/course-identities/{identity['id']}/unlink")
    assert response.status_code == 200, response.text
    assert response.json()["match_status"] == "unmatched"
    assert response.json()["course_id"] is None

    after = client.get("/api/v1/work-items").json()["items"]
    assert len(after) == before
    assert all(item["course_id"] is None for item in after)


def test_create_course_from_identity(client):
    _learning_connection(client)
    identity = identity_by_name(client, "数据库原理")["identity"]
    response = client.post(
        f"/api/v1/course-identities/{identity['id']}/create-course",
        json={"name": "数据库系统"},
    )
    assert response.status_code == 201, response.text
    course = response.json()
    assert course["name"] == "数据库系统"

    courses = client.get("/api/v1/courses").json()["items"]
    assert [item["id"] for item in courses] == [course["id"]]
    assert len(course["identities"]) == 1
    assert course["identities"][0]["id"] == identity["id"]
    remaining = {entry["identity"]["external_name"] for entry in unmatched_identities(client)}
    assert remaining == {"操作系统"}
