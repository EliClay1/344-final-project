"""
Everything that reads or writes tasks in Redis lives in this file.

The API never talks to Redis on its own, it calls the functions below.
So if we change how tasks are stored later, this is the only file that
has to change.

How tasks are laid out in Redis:

    task:<id>               one task, saved as JSON text
    task_screenshot:<id>    that task's screenshot, saved as base64 text
    task_queue              a list of task ids waiting for a worker
    tasks_running           a list of task ids a worker is on right now
    task_ids                a list of every task id, newest first
    user_task_ids:<id>      a list of one user's task ids, newest first
"""

import base64
import json
import os
import uuid
from datetime import datetime, timezone

import redis

# Where Redis is. On your own machine the default works. In Kubernetes
# the deployment sets REDIS_URL to point at the Redis service.
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

TASK_QUEUE = "task_queue"
TASKS_RUNNING = "tasks_running"
TASK_IDS = "task_ids"

TASK_TYPES = ["screenshot", "availability_check"]

# Screenshots get deleted after a day so Redis doesn't fill up.
SCREENSHOT_SECONDS = 24 * 60 * 60

# decode_responses=True makes Redis hand back normal strings instead of bytes.
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def task_key(task_id):
    return f"task:{task_id}"


def screenshot_key(task_id):
    return f"task_screenshot:{task_id}"


def user_task_ids_key(user_id):
    return f"user_task_ids:{user_id}"


def now():
    """The current time in UTC, as text like 2026-11-09T23:26:00+00:00."""
    return datetime.now(timezone.utc).isoformat()


def save_task(task):
    redis_client.set(task_key(task["id"]), json.dumps(task))


def get_task(task_id):
    """Returns the task as a dict, or None if there is no task with that id."""
    saved = redis_client.get(task_key(task_id))
    if saved is None:
        return None
    return json.loads(saved)


def create_task(url, task_type, user_id):
    """Saves a new task and puts it on the queue for a worker to pick up."""
    task = {
        "id": str(uuid.uuid4()),
        "url": url,
        "task_type": task_type,
        "status": "queued",
        "user_id": user_id,
        "active_agent": None,
        "attempts": 0,
        "created_at": now(),
        "started_at": None,
        "completed_at": None,
        "result": None,
        "error": None,
    }
    save_task(task)
    redis_client.lpush(TASK_IDS, task["id"])
    redis_client.lpush(user_task_ids_key(user_id), task["id"])

    # This is the line that hands the task to the workers. They wait on
    # the other end of this list and take ids off it one at a time.
    redis_client.lpush(TASK_QUEUE, task["id"])
    return task


def list_tasks(user_id=None, limit=50):
    """The most recent tasks, newest first. Give it a user_id to get only theirs."""
    if user_id is None:
        list_name = TASK_IDS
    else:
        list_name = user_task_ids_key(user_id)
    task_ids = redis_client.lrange(list_name, 0, limit - 1)
    tasks = [get_task(task_id) for task_id in task_ids]
    return [task for task in tasks if task is not None]


def tasks_waiting():
    """How many tasks are sitting on the queue with no worker yet."""
    return redis_client.llen(TASK_QUEUE)


def tasks_running():
    """How many tasks a worker is on right now."""
    return redis_client.llen(TASKS_RUNNING)


def save_screenshot(task_id, image_bytes):
    """
    Saves a task's screenshot. Everything else we keep in Redis is text,
    so the image gets turned into base64 text first.
    """
    image_text = base64.b64encode(image_bytes).decode()
    redis_client.set(screenshot_key(task_id), image_text, ex=SCREENSHOT_SECONDS)


def get_screenshot(task_id):
    """Returns the image as bytes, or None if that task has no screenshot."""
    image_text = redis_client.get(screenshot_key(task_id))
    if image_text is None:
        return None
    return base64.b64decode(image_text)
