"""
A pretend browser worker, so the backend can be tested before the real
one exists.

It does the same three things the real worker has to do:

    1. wait for a task id to show up on task_queue
    2. mark that task as running
    3. write a result (or an error) onto the task and mark it done

The only difference is that it never opens a browser. It waits a second
and makes the result up.

Run it with:  python fake_worker.py
"""

import time

import task_store

AGENT_NAME = "fake_worker"

# How long to pretend a page takes to load.
PRETEND_SECONDS = 1


def make_up_result(task):
    if task["task_type"] == "availability_check":
        return {"is_up": True, "http_status": 200, "load_time_ms": 412}
    # Where the screenshot image itself goes isn't decided yet, so for
    # now a screenshot result is only the page title.
    return {"page_title": "Fake page title"}


def work_on(task_id):
    task = task_store.get_task(task_id)
    if task is None:
        return

    task["status"] = "running"
    task["active_agent"] = AGENT_NAME
    task_store.save_task(task)

    time.sleep(PRETEND_SECONDS)

    # Put the word "fail" in a url to see what a failed task looks like.
    if "fail" in task["url"]:
        task["status"] = "failed"
        task["error"] = "the fake worker fails any url with 'fail' in it"
    else:
        task["status"] = "completed"
        task["result"] = make_up_result(task)

    task["completed_at"] = task_store.now()
    task_store.save_task(task)
    print(f"{task['status']}: {task['url']}")


def main():
    print("fake worker is waiting for tasks (ctrl+c to stop)")
    while True:
        # brpop waits here until an id is on the queue, then takes it off.
        # It hands back the queue's name and the id, and we only need the id.
        queue_name, task_id = task_store.redis_client.brpop(task_store.TASK_QUEUE)
        work_on(task_id)


if __name__ == "__main__":
    main()
