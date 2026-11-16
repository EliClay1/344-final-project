"""
Rescues tasks whose worker died.

When a worker dies in the middle of a task, nothing ever marks that
task as done, so it would say "running" forever. This script looks at
every task in tasks_running every few seconds. If one has been running
longer than TASK_TIMEOUT_SECONDS, we assume its worker is gone and put
the task back on the queue for another worker.

A task only gets MAX_ATTEMPTS tries. After that it's marked failed, so
a page that kills the browser every time can't go around forever.

TASK_TIMEOUT_SECONDS has to be longer than the longest a real worker
will ever spend on one page, or we'd take tasks away from workers that
are still fine.

Run it with:  python stuck_task_checker.py
"""

import time
from datetime import datetime, timezone

import task_store

TASK_TIMEOUT_SECONDS = 60
MAX_ATTEMPTS = 3
CHECK_EVERY_SECONDS = 5


def seconds_since(time_text):
    then = datetime.fromisoformat(time_text)
    return (datetime.now(timezone.utc) - then).total_seconds()


def is_stuck(task):
    if task["status"] != "running":
        return False
    return seconds_since(task["started_at"]) > TASK_TIMEOUT_SECONDS


def check_once():
    running_ids = task_store.redis_client.lrange(task_store.TASKS_RUNNING, 0, -1)
    for task_id in running_ids:
        task = task_store.get_task(task_id)
        if task is None or not is_stuck(task):
            continue

        task_store.redis_client.lrem(task_store.TASKS_RUNNING, 0, task_id)

        if task["attempts"] >= MAX_ATTEMPTS:
            task["status"] = "failed"
            task["error"] = f"gave up after {MAX_ATTEMPTS} tries, the worker never finished"
            task["completed_at"] = task_store.now()
            task_store.save_task(task)
            print(f"gave up on: {task['url']}")
        else:
            task["status"] = "queued"
            task["active_agent"] = None
            task["started_at"] = None
            task_store.save_task(task)
            # rpush puts it at the front of the line (workers take from
            # the right side), since it already waited its turn once.
            task_store.redis_client.rpush(task_store.TASK_QUEUE, task_id)
            print(f"put back on the queue: {task['url']}")


def main():
    print("checking for stuck tasks (ctrl+c to stop)")
    while True:
        check_once()
        time.sleep(CHECK_EVERY_SECONDS)


if __name__ == "__main__":
    main()
