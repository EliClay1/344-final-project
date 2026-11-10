"""
Sends a batch of tasks through the real API and times how long the
workers take to finish them. It goes through the same endpoints the
dashboard uses, so it tests the whole path:

    load_test.py  -->  API  -->  Redis  <--  workers

Run it with:
    python load_test.py --count 50 --task-type screenshot --url https://example.com

Only uses the Python standard library, so there's nothing to install.
"""

import argparse
import json
import time
import urllib.error
import urllib.request
from collections import Counter

parser = argparse.ArgumentParser()
parser.add_argument("--api", default="http://localhost:8000")
parser.add_argument("--url", action="append", help="can be given more than once, tasks take turns")
parser.add_argument("--task-type", default="availability_check", choices=["availability_check", "screenshot"])
parser.add_argument("--count", type=int, default=20)
parser.add_argument("--username", default="load_tester")
parser.add_argument("--password", default="load_test_password")
args = parser.parse_args()
urls = args.url or ["https://example.com"]


def call(method, path, body=None, token=None):
    request = urllib.request.Request(args.api + path, method=method)
    request.add_header("content-type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(request, data) as response:
        return json.loads(response.read())


# Make the account the first time, then log in.
try:
    call("POST", "/users", {"username": args.username, "password": args.password})
except urllib.error.HTTPError:
    pass  # it already exists
token = call("POST", "/login", {"username": args.username, "password": args.password})["token"]

started = time.time()
task_ids = []
for number in range(args.count):
    task = call("POST", "/tasks", {"url": urls[number % len(urls)], "task_type": args.task_type}, token)
    task_ids.append(task["id"])
print(f"submitted {len(task_ids)} {args.task_type} tasks in {time.time() - started:.1f}s")

while True:
    tasks = [call("GET", f"/tasks/{task_id}", token=token) for task_id in task_ids]
    statuses = Counter(task["status"] for task in tasks)
    health = call("GET", "/health")
    print(f"\r{time.time() - started:6.1f}s  waiting={health['tasks_waiting']:4d}  "
          f"running={health['tasks_running']:3d}  {dict(statuses)}   ", end="", flush=True)
    if statuses["completed"] + statuses["failed"] == len(tasks):
        break
    time.sleep(1)

took = time.time() - started
print(f"\nall done in {took:.1f}s ({len(tasks) / took:.2f} tasks per second)")
print("workers used:", dict(Counter(task["active_agent"] for task in tasks)))
retried = sum(1 for task in tasks if task["attempts"] > 1)
if retried:
    print(f"{retried} tasks needed more than one try")
failures = Counter(task["error"].split(":")[0] for task in tasks if task["error"])
if failures:
    print("failures by kind:", dict(failures))
