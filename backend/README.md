# Backend

This is the API for our 344 final project. It takes in tasks from the dashboard and saves them in Redis, and when the dashboard asks how a task is going it reads the answer back out of Redis. It's three short Python files and I tried to keep it simple enough that you can read the whole thing in one sitting.

## How does a task get from the dashboard to a worker?

Through a list in Redis called `task_queue`. When someone submits a url, the API saves a task and pushes its id onto that list. The workers are all waiting on the other end of the list, so one of them takes the id off, does the browser stuff, and writes what it found back onto the same task in Redis.

```
dashboard  -->  API  -->  Redis  <--  workers
```

The API and the workers never talk to each other, they both only talk to Redis. So the API has no idea how many workers there are, and Kubernetes can add or remove them whenever it wants. The length of `task_queue` is also a number KEDA can watch to decide how many workers to run.

## What does a task look like?

```json
{
  "id": "056c0ab7-824e-4e2e-b2ca-e624bec587aa",
  "url": "https://byu.edu",
  "task_type": "availability_check",
  "status": "completed",
  "active_agent": "fake_worker",
  "created_at": "2026-11-10T01:27:33.825646+00:00",
  "completed_at": "2026-11-10T01:27:35.966721+00:00",
  "result": {"is_up": true, "http_status": 200, "load_time_ms": 412},
  "error": null
}
```

`status` starts at `queued`, goes to `running` when a worker picks the task up, and ends at `completed` or `failed`. `result` is whatever the worker found and it stays null until the task is completed. `error` is the reason if it failed. `active_agent` is the name of the worker that picked it up. All the times are UTC.

`id`, `url`, `active_agent`, `created_at` and `completed_at` are from Eli's object diagram. I added `task_type`, `status`, `result` and `error`, since the worker has to know which kind of task it's doing and the dashboard needs something to show.

## What are the endpoints?

| Endpoint | What it does |
|---|---|
| `POST /tasks` | Submits a task. Send `{"url": "https://example.com", "task_type": "screenshot"}` and you get the new task back. `task_type` is `screenshot` or `availability_check` (screenshot if you leave it off). |
| `GET /tasks` | The 50 most recent tasks, newest first. |
| `GET /tasks/<id>` | One task. The dashboard can call this every second or so to watch the status change. |
| `GET /health` | Says whether the API is up and can reach Redis, and how many tasks are waiting for a worker. |

A bad url or a `task_type` we don't have gets a 400 back with the reason, and an id that doesn't exist gets a 404.

FastAPI also makes a docs page on its own at `/docs`, where you can try every endpoint from the browser without writing any code.

## How do I run it?

You need Python and Redis. From this folder:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Then start Redis in its own terminal. On a Mac that's `brew install redis` once and then `redis-server`.

Then start the API and open http://localhost:8000/docs.

```
uvicorn app:app --reload
```

If Redis is on a different machine, tell the API where before you start it, like `export REDIS_URL=redis://some_host:6379/0`.

## How do I try it without the real worker?

Run the fake one in another terminal.

```
python fake_worker.py
```

It takes tasks off the queue the same way the real worker will, waits a second, and makes up a result. Any url with the word "fail" in it fails on purpose, so you can see what a failed task looks like too.

Then submit a task and look at it a couple seconds later.

```
curl -X POST localhost:8000/tasks -H "content-type: application/json" -d '{"url": "https://example.com"}'
curl localhost:8000/tasks
```

## What does the real worker need to do?

Three things, and `fake_worker.py` does all three if you want to see them in code.

1. Wait for a task id with `BRPOP task_queue`.
2. `GET task:<id>`, set `status` to `running` and `active_agent` to its own name, and `SET` it back.
3. When it's done, set `status` to `completed` and fill in `result` (or `failed` and fill in `error`), set `completed_at`, and `SET` it back.

A task is saved as plain JSON text, so this works from any language that has a Redis library.

## How do I run the tests?

Run `pytest` from this folder. The tests use fakeredis (a pretend Redis that lives in memory), so Redis doesn't have to be running.

## What's in each file?

| File | What's in it |
|---|---|
| `app.py` | The endpoints. |
| `task_store.py` | Everything that reads or writes Redis. |
| `fake_worker.py` | The pretend worker. |
| `test_backend.py` | The tests. |

## What isn't built yet?

Logins. Eli's diagram has a User object with a password and a permission level, and none of that is in here, so right now anyone who can reach the API can submit a task and see every task.

Screenshots. A task has a spot for a result, but we haven't decided where the image itself gets saved (it can't be the worker's own disk, since workers come and go).

Crash recovery. If a worker dies in the middle of a task, the task says `running` forever, because its id already came off the queue. We want to show recovery in the demo so this needs an answer, and it depends on how the workers and Kubernetes end up working.
