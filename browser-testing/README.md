# Browser Worker

This is the worker that replaces `backend/fake_worker.py`. It does the exact same thing as Noah's fake worker. It takes task ids off of task_queue, opens each of them in Chromium using playwrite, and then rights the result back onto the given task in Redis. It only communicated with Redis.

```
(Copied from backend/README.md)
dashboard  -->  API  -->  Redis  <--  workers (this folder)
```

## How it fits the backend

It does the same four steps the `backend/README.md` lists, using the same key names as `backend/task_store.py`:

1. `blmove(task_store.TASK_QUEUE, task_store.TASKS_RUNNING, 2, src="RIGHT", dest="LEFT")`, asking again every 2 seconds.
2. `GET task:<id>`, set `status: running`, `active_agent`, `started_at`, add 1 to `attempts`, and `SET` it back.
3. Open the page, then fill in `status` (`completed` or `failed`), `result` or `error`, and `completed_at`. Screenshots go to `task_screenshot:<id>` as base64 text with `EX 86400`.
4. `LREM tasks_running 0 <id>`.

It doesn't do any crash recovery of its own. If a worker dies, the backend's `stuck_task_checker.py` puts the task back after 60 seconds and gives up after 3 tries. The worker just has to stay out of the checker's way:

- A whole task is cut off at `TASK_LIMIT_SECONDS` (40). The worker refuses to start if that's set within 10 seconds of the checker's 60.
- Before saving a result, it re-reads the task. If the checker already handed it to another worker (a different `active_agent` or `started_at`), it throws its own result away so the two don't overwrite each other.
- If a task id is on the queue but `task:<id>` is gone, it still removes the id from `tasks_running`. Otherwise the id would sit there forever, since the checker skips missing tasks.

### Results
The keys `fake_worker.py` makes are all still there, so the dashboard won't need to change. The extras are marked.

| task_type | result |
|---|---|
| `availability_check` | `is_up`, `http_status`, `load_time_ms`, plus `page_title` and `final_url` (extras) |
| `screenshot` | `page_title`, plus `http_status`, `load_time_ms`, `final_url` and `screenshot_bytes` (extras). The image goes in `task_screenshot:<id>`. |

A site answering 404 or 503 is still a `completed` task with `is_up: false`. The worker did its job, the site is just down.

### Errors
`error` is plain text the dashboard can show as-is. It always starts with one of these words and a colon, so the load test can count failures by kind:

| Starts with | Means |
| --- | --- |
| `timeout:` | the page took longer than `PAGE_LOAD_SECONDS` (15) |
| `dns:` | the website's name doesn't exist |
| `connection:` / `network:` / `tls:` | couldn't connect, or the certificate is bad |
| `blocked:` | the url (or something the page loaded) points at a private address |
| `bad_url:` / `bad_task:` | not http(s), or an unknown `task_type` |
| `browser_crash:` | Chromium crashed, and it gets restarted for the next task |
| `worker_error:` | anything else, with the Python error name |

## Running it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install playwright redis
playwright install --with-deps chromium

# try some urls with no Redis (screenshots get saved to ./screenshots)
python worker.py --local sample_tasks.json

# the real thing: start Redis, the API and stuck_task_checker.py as the backend README says, then
python worker.py
```

Start `python worker.py` in a couple of terminals with different names (`AGENT_NAME=worker-a python worker.py`) to watch them split the queue.

With Docker, `docker compose up --build --scale worker=3` starts Redis and three workers, and the backend running on your machine reaches that Redis on `localhost:6379`.

## Load testing

`load_test.py` goes through the real API, the same way the dashboard does. It makes an account, submits tasks, polls `/tasks/<id>` and `/health`, and reports the time, which workers did what, retries, and failures by kind.

```bash
python load_test.py --count 50 --task-type screenshot --url https://example.com --url https://byu.edu
```

## Settings

| Variable | Default | What it does |
| --- | --- | --- |
| `REDIS_URL` | `redis://localhost:6379/0` | Same as the backend |
| `AGENT_NAME` | hostname (the pod name in Kubernetes) | What shows up in `active_agent` |
| `PAGE_LOAD_SECONDS` | 15 | Most time a page gets to load |
| `TASK_LIMIT_SECONDS` | 40 | Most time a whole task gets, has to stay under 50 |
| `TASKS_PER_BROWSER` | 50 | Start a fresh Chromium after this many tasks |
| `SCREEN_WIDTH` / `SCREEN_HEIGHT` | 1280 / 800 | Screenshot size |
| `FULL_PAGE` | false | Capture the whole page, not just the top |
| `ALLOW_PRIVATE_URLS` | false | Lets the worker open private addresses, testing only |
| `CHROMIUM_SANDBOX` | false | Chromium's own sandbox, which needs a seccomp profile in the container |

## For security testing

- The worker refuses private, loopback and cloud-metadata addresses (`169.254.169.254`) for the url, for everything the page loads, and for wherever a redirect ends up. Playwright skips its request check on redirect hops, and DNS tricks can get around any check done in code. So the real wall should be a Kubernetes NetworkPolicy that only lets workers reach Redis, DNS, and public ports 80 and 443.
- The API checks that a url starts with http(s), but it doesn't check where the url points, so the worker's check is the only one right now.
- `/tasks/<id>/screenshot` doesn't need a login, by design. Anyone with a task id can see that screenshot.

## Notes for the backend

None of these block the worker, but they're worth bringing up:

- In `fake_worker.py`, when `task:<id>` is missing, `work_on` returns before the `LREM`, so the id stays in `tasks_running` for good. The real worker cleans it up, but the checker could also drop ids whose task is gone.
- Each update reads the task, changes it, and writes it back (`GET` then `SET`), so two writers at once could overwrite each other. The take-over check above covers the worker side. A `WATCH`/`MULTI` or a small Lua script would make it airtight if it ever matters.
- Since the checker waits 60 seconds, every crash adds about a minute to that task. A shorter `TASK_TIMEOUT_SECONDS`, like 50, would still be safe with the worker's 40-second limit.

## Experiments to try

1. **Cold start.** How long from KEDA adding a pod to its first `task_completed`? Look at `browser_started.took_ms` and the pod start time.
2. **Browser recycling.** Run 500 tasks with `TASKS_PER_BROWSER` set to 1, 10, 50 and 200, and compare memory, speed and crashes.
3. **Chaos.** `kubectl delete pod --grace-period=0 --force` during a batch, and an OOM kill (set the memory limit to 300Mi). Check that nothing is lost and that `attempts` counts are right.
4. **A page that always crashes.** It should end up `failed` after 3 tries instead of looping forever.
5. **The load curve.** Run `load_test.py --count` at 50, 200 and 1000, and graph queue length, number of workers, and tasks per second over time. That's the main graph for the project.
