"""
A pretend browser worker, so the backend can be tested before the real
one exists.

It does the same things the real worker has to do:

    1. wait for a task id, and move it from task_queue to tasks_running
    2. mark that task as running
    3. write a result (or an error) onto the task and mark it done
    4. take the id back off tasks_running

The only difference is that it never opens a browser. It waits a second
and makes the result up.

Two urls do something special, so you can see the unhappy paths too:
    a url with "fail" in it fails
    a url with "crash" in it kills the fake worker in the middle of the task

Run it with:  python fake_worker.py
"""

import sys
import time

import task_store

AGENT_NAME = "fake_worker"

# How long to pretend a page takes to load.
PRETEND_SECONDS = 1


def wait_for_task():
    # blmove waits for an id to show up on task_queue, then moves it over
    # to tasks_running in one step. If this worker dies in the middle of
    # the task, the id is still sitting in tasks_running, and that's how
    # stuck_task_checker.py finds it.
    #
    # It waits 2 seconds at a time and hands back None if nothing showed
    # up, so we keep asking. (Waiting forever in one go doesn't work, the
    # Python Redis library hangs up on any wait longer than 5 seconds.)
    while True:
        task_id = task_store.redis_client.blmove(
            task_store.TASK_QUEUE, task_store.TASKS_RUNNING, 2, src="RIGHT", dest="LEFT"
        )
        if task_id is not None:
            return task_id


def work_on(task_id):
    task = task_store.get_task(task_id)
    if task is None:
        return

    task["status"] = "running"
    task["active_agent"] = AGENT_NAME
    task["started_at"] = task_store.now()
    task["attempts"] += 1
    task_store.save_task(task)

    time.sleep(PRETEND_SECONDS)

    if "crash" in task["url"]:
        sys.exit("fake worker crashed on purpose (the url had 'crash' in it)")

    if "fail" in task["url"]:
        task["status"] = "failed"
        task["error"] = "the fake worker fails any url with 'fail' in it"
    elif task["task_type"] == "availability_check":
        task["status"] = "completed"
        task["result"] = {"is_up": True, "http_status": 200, "load_time_ms": 412}
    else:
        with open("fake_screenshot.png", "rb") as image_file:
            task_store.save_screenshot(task["id"], image_file.read())
        task["status"] = "completed"
        task["result"] = {"page_title": "Fake page title"}

    task["completed_at"] = task_store.now()
    task_store.save_task(task)
    task_store.redis_client.lrem(task_store.TASKS_RUNNING, 0, task_id)
    print(f"{task['status']}: {task['url']}")


def main():
    print("fake worker is waiting for tasks (ctrl+c to stop)")
    while True:
        work_on(wait_for_task())


if __name__ == "__main__":
    main()
