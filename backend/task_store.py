"""
Everything that reads or writes tasks in Redis lives in this file.

The API never talks to Redis on its own, it calls the functions below.
So if we change how tasks are stored later, this is the only file that
has to change.

How tasks are laid out in Redis:

    task:<id>     one task, saved as a JSON string
    task_queue    a list of task ids waiting for a worker
    task_ids      a list of every task id, newest first
"""

import json
import os
import uuid
from datetime import datetime, timezone

import redis

# Where Redis is. On your own machine the default works. In Kubernetes
# the deployment sets REDIS_URL to point at the Redis service.
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

TASK_QUEUE = "task_queue"
TASK_IDS = "task_ids"

TASK_TYPES = ["screenshot", "availability_check"]

# decode_responses=True makes Redis hand back normal strings instead of bytes.
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)


def task_key(task_id):
    return f"task:{task_id}"


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


def create_task(url, task_type):
    """Saves a new task and puts it on the queue for a worker to pick up."""
    task = {
        "id": str(uuid.uuid4()),
        "url": url,
        "task_type": task_type,
        "status": "queued",
        "active_agent": None,
        "created_at": now(),
        "completed_at": None,
        "result": None,
        "error": None,
    }
    save_task(task)
    redis_client.lpush(TASK_IDS, task["id"])

    # This is the line that hands the task to the workers. They wait on
    # the other end of this list and take ids off it one at a time.
    redis_client.lpush(TASK_QUEUE, task["id"])
    return task


def list_tasks(limit=50):
    """The most recent tasks, newest first."""
    task_ids = redis_client.lrange(TASK_IDS, 0, limit - 1)
    tasks = [get_task(task_id) for task_id in task_ids]
    return [task for task in tasks if task is not None]


def tasks_waiting():
    """How many tasks are sitting on the queue with no worker yet."""
    return redis_client.llen(TASK_QUEUE)
