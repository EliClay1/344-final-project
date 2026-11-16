import json
import subprocess
from uuid import uuid4

with open("sample_tasks.json", encoding="utf-8") as file:
    samples = json.load(file)

if not isinstance(samples, list) or not samples:
    raise SystemExit("Expected a non-empty JSON array of sample tasks.")

tasks = []
for number, sample in enumerate(samples[:9], start=1):
    if not isinstance(sample, dict) or not sample.get("url"):
        raise SystemExit(f"Sample {number} is missing a URL.")
    task = {**sample, "id": str(uuid4()), "status": "queued", "attempts": 0}
    task.setdefault("task_type", "screenshot")
    if task["task_type"] not in ("screenshot", "availability_check"):
        raise SystemExit(f"Sample {number} has an unsupported task_type.")
    tasks.append(task)

redis = [
    "sudo", "k3s", "kubectl", "-n", "browser-lab",
    "exec", "deployment/redis", "--", "redis-cli", "-e",
]

for task in tasks:
    subprocess.run([*redis, "SET", f"task:{task['id']}", json.dumps(task)], check=True)

task_ids = [task["id"] for task in tasks]
subprocess.run([*redis, "LPUSH", "task_queue", *task_ids], check=True)
print(f"Queued {len(task_ids)} tasks. First task ID: {task_ids[0]}")
