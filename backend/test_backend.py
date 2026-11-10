"""
Tests for the backend. Run them with:  pytest

They use fakeredis, which is a pretend Redis that lives in memory, so
you don't need Redis running to run these.
"""

import fakeredis
import pytest
from fastapi.testclient import TestClient

import fake_worker
import stuck_task_checker
import task_store
import user_store
from app import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def use_fake_redis(monkeypatch):
    """Runs before every test. Each test gets its own empty pretend Redis."""
    monkeypatch.setattr(
        task_store, "redis_client", fakeredis.FakeRedis(decode_responses=True)
    )
    monkeypatch.setattr(fake_worker, "PRETEND_SECONDS", 0)
    # Real password hashing is slow on purpose. Turn it down so tests are quick.
    monkeypatch.setattr(user_store, "HASH_ROUNDS", 4)


def log_in_as(username, password="a_good_password"):
    """Makes an account, logs in, and returns the header to send with requests."""
    client.post("/users", json={"username": username, "password": password})
    login = client.post("/login", json={"username": username, "password": password})
    return {"Authorization": f"Bearer {login.json()['token']}"}


def submit(headers, url="https://example.com", task_type="screenshot"):
    return client.post(
        "/tasks", json={"url": url, "task_type": task_type}, headers=headers
    )


def start_working_on_next_task():
    """Does what a worker does up to the point where it could die."""
    task_id = fake_worker.wait_for_task()
    task = task_store.get_task(task_id)
    task["status"] = "running"
    task["started_at"] = task_store.now()
    task["attempts"] += 1
    task_store.save_task(task)
    return task


def pretend_it_started_long_ago(task):
    task["started_at"] = "2020-01-01T00:00:00+00:00"
    task_store.save_task(task)


# ---- accounts and logging in ----


def test_making_an_account():
    response = client.post(
        "/users", json={"username": "noah", "password": "a_good_password"}
    )

    assert response.status_code == 201
    assert response.json()["username"] == "noah"
    assert response.json()["permission_level"] == 0


def test_the_password_is_never_saved_or_sent_back():
    response = client.post(
        "/users", json={"username": "noah", "password": "a_good_password"}
    )

    saved = task_store.redis_client.get("user:noah")
    assert "a_good_password" not in saved
    assert "password" not in response.text


def test_a_username_can_only_be_used_once():
    client.post("/users", json={"username": "noah", "password": "a_good_password"})

    response = client.post(
        "/users", json={"username": "noah", "password": "another_password"}
    )

    assert response.status_code == 400


def test_a_short_password_is_refused():
    response = client.post("/users", json={"username": "noah", "password": "short"})

    assert response.status_code == 400


def test_a_weird_username_is_refused():
    response = client.post(
        "/users", json={"username": "no spaces!", "password": "a_good_password"}
    )

    assert response.status_code == 400


def test_logging_in_gives_you_a_token():
    client.post("/users", json={"username": "noah", "password": "a_good_password"})

    response = client.post(
        "/login", json={"username": "noah", "password": "a_good_password"}
    )

    assert response.status_code == 200
    assert len(response.json()["token"]) > 20
    assert response.json()["user"]["username"] == "noah"


def test_the_wrong_password_does_not_log_you_in():
    client.post("/users", json={"username": "noah", "password": "a_good_password"})

    response = client.post(
        "/login", json={"username": "noah", "password": "not_the_password"}
    )

    assert response.status_code == 401


def test_tasks_need_a_login():
    no_token = client.get("/tasks")
    bad_token = client.get("/tasks", headers={"Authorization": "Bearer made_up"})

    assert no_token.status_code == 401
    assert bad_token.status_code == 401


# ---- submitting and reading tasks ----


def test_submitting_a_task_saves_it_and_queues_it():
    response = submit(log_in_as("noah"))
    task = response.json()

    assert response.status_code == 201
    assert task["url"] == "https://example.com"
    assert task["task_type"] == "screenshot"
    assert task["status"] == "queued"
    assert task["attempts"] == 0
    assert task_store.redis_client.lrange("task_queue", 0, -1) == [task["id"]]


def test_task_type_defaults_to_screenshot():
    response = client.post(
        "/tasks", json={"url": "https://example.com"}, headers=log_in_as("noah")
    )

    assert response.json()["task_type"] == "screenshot"


def test_getting_a_task_by_id():
    noah = log_in_as("noah")
    task = submit(noah).json()

    response = client.get(f"/tasks/{task['id']}", headers=noah)

    assert response.status_code == 200
    assert response.json() == task


def test_getting_a_task_that_does_not_exist():
    response = client.get("/tasks/not_a_real_id", headers=log_in_as("noah"))

    assert response.status_code == 404


def test_url_has_to_be_http_or_https():
    response = submit(log_in_as("noah"), url="ftp://example.com")

    assert response.status_code == 400


def test_task_type_has_to_be_one_we_know():
    response = submit(log_in_as("noah"), task_type="mine_bitcoin")

    assert response.status_code == 400


def test_listing_tasks_shows_newest_first():
    noah = log_in_as("noah")
    first = submit(noah, url="https://first.example.com").json()
    second = submit(noah, url="https://second.example.com").json()

    tasks = client.get("/tasks", headers=noah).json()

    assert [task["id"] for task in tasks] == [second["id"], first["id"]]


def test_health_counts_tasks_waiting():
    noah = log_in_as("noah")
    submit(noah)
    submit(noah)

    response = client.get("/health")

    assert response.json() == {"status": "ok", "tasks_waiting": 2, "tasks_running": 0}


# ---- who can see what ----


def test_you_only_see_your_own_tasks():
    noah = log_in_as("noah")
    eli = log_in_as("eli")
    noahs_task = submit(noah).json()
    elis_task = submit(eli).json()

    noahs_list = client.get("/tasks", headers=noah).json()
    peek = client.get(f"/tasks/{elis_task['id']}", headers=noah)

    assert [task["id"] for task in noahs_list] == [noahs_task["id"]]
    assert peek.status_code == 404


def test_an_admin_sees_everyones_tasks():
    noah = log_in_as("noah")
    eli = log_in_as("eli")
    submit(noah)
    elis_task = submit(eli).json()

    user_store.make_admin("noah")
    everything = client.get("/tasks", headers=noah).json()
    peek = client.get(f"/tasks/{elis_task['id']}", headers=noah)

    assert len(everything) == 2
    assert peek.status_code == 200


# ---- the fake worker and screenshots ----


def test_fake_worker_completes_a_task():
    noah = log_in_as("noah")
    task = submit(noah, task_type="availability_check").json()

    fake_worker.work_on(fake_worker.wait_for_task())
    finished = client.get(f"/tasks/{task['id']}", headers=noah).json()

    assert finished["status"] == "completed"
    assert finished["active_agent"] == "fake_worker"
    assert finished["attempts"] == 1
    assert finished["result"]["http_status"] == 200
    assert finished["started_at"] is not None
    assert finished["completed_at"] is not None
    assert task_store.tasks_running() == 0


def test_fake_worker_fails_a_url_with_fail_in_it():
    noah = log_in_as("noah")
    task = submit(noah, url="https://fail.example.com").json()

    fake_worker.work_on(fake_worker.wait_for_task())
    finished = client.get(f"/tasks/{task['id']}", headers=noah).json()

    assert finished["status"] == "failed"
    assert finished["result"] is None
    assert finished["error"] is not None


def test_a_screenshot_task_ends_up_with_an_image():
    task = submit(log_in_as("noah")).json()

    fake_worker.work_on(fake_worker.wait_for_task())
    response = client.get(f"/tasks/{task['id']}/screenshot")

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    # Every PNG file starts with these same few bytes.
    assert response.content.startswith(b"\x89PNG")


def test_no_screenshot_gives_a_404():
    task = submit(log_in_as("noah")).json()

    response = client.get(f"/tasks/{task['id']}/screenshot")

    assert response.status_code == 404


# ---- a worker dying ----


def test_a_crash_leaves_the_task_stuck_on_running():
    noah = log_in_as("noah")
    task = submit(noah, url="https://crash.example.com").json()

    with pytest.raises(SystemExit):
        fake_worker.work_on(fake_worker.wait_for_task())
    stuck = client.get(f"/tasks/{task['id']}", headers=noah).json()

    assert stuck["status"] == "running"
    assert task_store.redis_client.lrange("tasks_running", 0, -1) == [task["id"]]


def test_a_stuck_task_goes_back_on_the_queue():
    submit(log_in_as("noah"))
    task = start_working_on_next_task()
    pretend_it_started_long_ago(task)

    stuck_task_checker.check_once()
    rescued = task_store.get_task(task["id"])

    assert rescued["status"] == "queued"
    assert rescued["attempts"] == 1
    assert task_store.redis_client.lrange("task_queue", 0, -1) == [task["id"]]
    assert task_store.tasks_running() == 0


def test_a_task_that_just_started_is_left_alone():
    submit(log_in_as("noah"))
    task = start_working_on_next_task()

    stuck_task_checker.check_once()

    assert task_store.get_task(task["id"])["status"] == "running"
    assert task_store.tasks_running() == 1


def test_a_task_fails_for_good_after_three_tries():
    submit(log_in_as("noah"))

    for attempt in range(3):
        task = start_working_on_next_task()
        pretend_it_started_long_ago(task)
        stuck_task_checker.check_once()
    given_up = task_store.get_task(task["id"])

    assert given_up["status"] == "failed"
    assert given_up["attempts"] == 3
    assert task_store.tasks_waiting() == 0
    assert task_store.tasks_running() == 0
