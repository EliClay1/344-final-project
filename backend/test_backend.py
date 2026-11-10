"""
Tests for the backend. Run them with:  pytest

They use fakeredis, which is a pretend Redis that lives in memory, so
you don't need Redis running to run these.
"""

import fakeredis
import pytest
from fastapi.testclient import TestClient

import fake_worker
import task_store
from app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def use_fake_redis(monkeypatch):
    """Runs before every test. Each test gets its own empty pretend Redis."""
    monkeypatch.setattr(
        task_store, "redis_client", fakeredis.FakeRedis(decode_responses=True)
    )
    monkeypatch.setattr(fake_worker, "PRETEND_SECONDS", 0)


def submit(url="https://example.com", task_type="screenshot"):
    return client.post("/tasks", json={"url": url, "task_type": task_type})


def test_submitting_a_task_saves_it_and_queues_it():
    response = submit()
    task = response.json()

    assert response.status_code == 201
    assert task["url"] == "https://example.com"
    assert task["task_type"] == "screenshot"
    assert task["status"] == "queued"
    assert task["completed_at"] is None
    assert task_store.redis_client.lrange("task_queue", 0, -1) == [task["id"]]


def test_task_type_defaults_to_screenshot():
    response = client.post("/tasks", json={"url": "https://example.com"})

    assert response.json()["task_type"] == "screenshot"


def test_getting_a_task_by_id():
    task = submit().json()

    response = client.get(f"/tasks/{task['id']}")

    assert response.status_code == 200
    assert response.json() == task


def test_getting_a_task_that_does_not_exist():
    response = client.get("/tasks/not_a_real_id")

    assert response.status_code == 404


def test_url_has_to_be_http_or_https():
    response = submit(url="ftp://example.com")

    assert response.status_code == 400


def test_task_type_has_to_be_one_we_know():
    response = submit(task_type="mine_bitcoin")

    assert response.status_code == 400


def test_listing_tasks_shows_newest_first():
    first = submit(url="https://first.example.com").json()
    second = submit(url="https://second.example.com").json()

    tasks = client.get("/tasks").json()

    assert [task["id"] for task in tasks] == [second["id"], first["id"]]


def test_health_counts_tasks_waiting():
    submit()
    submit()

    response = client.get("/health")

    assert response.json() == {"status": "ok", "tasks_waiting": 2}


def test_fake_worker_completes_a_task():
    task = submit(task_type="availability_check").json()

    fake_worker.work_on(task["id"])
    finished = client.get(f"/tasks/{task['id']}").json()

    assert finished["status"] == "completed"
    assert finished["active_agent"] == "fake_worker"
    assert finished["result"]["http_status"] == 200
    assert finished["completed_at"] is not None
    assert finished["error"] is None


def test_fake_worker_fails_a_url_with_fail_in_it():
    task = submit(url="https://fail.example.com").json()

    fake_worker.work_on(task["id"])
    finished = client.get(f"/tasks/{task['id']}").json()

    assert finished["status"] == "failed"
    assert finished["result"] is None
    assert finished["error"] is not None
