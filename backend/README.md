# Backend

This is the API for our 344 final project. It takes in tasks from the dashboard and saves them in Redis, and when the dashboard asks how a task is going it reads the answer back out of Redis. It also does logins, hands out screenshots, and rescues tasks when a worker dies. It's a handful of short Python files and I tried to keep it simple enough that you can read the whole thing in one sitting.

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
  "user_id": "adaa70b5-9129-4d82-bdc0-afbf76aeb672",
  "active_agent": "fake_worker",
  "attempts": 1,
  "created_at": "2026-11-10T01:27:33.825646+00:00",
  "started_at": "2026-11-10T01:27:34.966721+00:00",
  "completed_at": "2026-11-10T01:27:35.966721+00:00",
  "result": {"is_up": true, "http_status": 200, "load_time_ms": 412},
  "error": null
}
```

`status` starts at `queued`, goes to `running` when a worker picks the task up, and ends at `completed` or `failed`. `result` is whatever the worker found and it stays null until the task is completed. `error` is the reason if it failed. `active_agent` is the name of the worker that picked it up, and `attempts` is how many times a worker has started it. All the times are UTC.

`id`, `url`, `active_agent`, `created_at` and `completed_at` are from Eli's object diagram. I added the rest, since the worker has to know which kind of task it's doing and the dashboard needs something to show.

## What are the endpoints?

| Endpoint | Login? | What it does |
|---|---|---|
| `POST /users` | no | Makes an account. Send `{"username": "noah", "password": "..."}`. |
| `POST /login` | no | Send the same thing and you get a `token` back. |
| `POST /tasks` | yes | Submits a task. Send `{"url": "https://example.com", "task_type": "screenshot"}` and you get the new task back. `task_type` is `screenshot` or `availability_check` (screenshot if you leave it off). |
| `GET /tasks` | yes | Your 50 most recent tasks, newest first. An admin gets everyone's. |
| `GET /tasks/<id>` | yes | One task. The dashboard can call this every second or so to watch the status change. |
| `GET /tasks/<id>/screenshot` | no | The screenshot for a task, as a PNG. |
| `GET /health` | no | Says whether the API is up and can reach Redis, and how many tasks are waiting and running. |

Bad input gets a 400 back with the reason, a missing or wrong token gets a 401, and an id that doesn't exist gets a 404.

FastAPI also makes a docs page on its own at `/docs`, where you can try every endpoint from the browser without writing any code. For the ones that need a login, hit the Authorize button at the top and paste in your token.

## How do logins work?

You make an account, log in, and get a token, which is a long random string. Then you send that token with every request in a header that looks like `Authorization: Bearer <token>`. A token works for a day and then you log in again.

Passwords are never saved. What gets saved is a hash (scrambled text that can't be turned back into the password), and to check a login we hash what you typed and see if it matches.

Everyone starts at permission level 0, which means you only see your own tasks. Level 2 is an admin, who sees everyone's. There's no endpoint to make an admin, you have to be on the machine and run `python make_admin.py <username>`.

## Where do screenshots go?

Into Redis, right next to the task, under `task_screenshot:<id>`. Every worker can already reach Redis, so there's nothing extra to set up. They get deleted after a day so Redis doesn't fill up.

The dashboard shows one by pointing an image tag at `/tasks/<id>/screenshot`. That endpoint doesn't ask for a token, since an image tag can't send one. The task id is a long random string that nobody can guess, and that's what keeps other people out.

## What happens if a worker dies?

The task gets put back on the queue for another worker. While a worker has a task, its id sits in a second list called `tasks_running`. `stuck_task_checker.py` looks through that list every 5 seconds, and any task that has been running for more than 60 seconds goes back on the queue (at the front, since it already waited once).

A task gets 3 tries. After that it's marked `failed`, so a page that kills the browser every time can't go around forever.

The 60 seconds has to be longer than the longest a worker will ever spend on one page, or we'd take tasks away from workers that are still fine. It's `TASK_TIMEOUT_SECONDS` at the top of that file if it needs to change.

## How do I run it?

You need Python and Redis. From this folder:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Ubuntu the first line fails until you run `sudo apt install python3-venv` (kube-lab doesn't have it yet).

Then start Redis in its own terminal. On a Mac that's `brew install redis` once and then `redis-server`.

Then start the API and open http://localhost:8000/docs.

```
uvicorn app:app --reload
```

If Redis is on a different machine, tell the API where before you start it, like `export REDIS_URL=redis://some_host:6379/0`.

## How do I try it without the real worker?

Run the fake one in another terminal, and the checker in one more if you want to see a task get rescued.

```
python fake_worker.py
python stuck_task_checker.py
```

The fake worker takes tasks off the queue the same way the real one will, waits a second, and makes up a result (screenshot tasks all get the same picture). Two urls do something special. Any url with "fail" in it fails, and any url with "crash" in it kills the fake worker in the middle of the task, so you can start it again and watch the checker put that task back a minute later.

Then make an account, log in, and submit a task.

```
curl -X POST localhost:8000/users -H "content-type: application/json" -d '{"username": "noah", "password": "a_good_password"}'
curl -X POST localhost:8000/login -H "content-type: application/json" -d '{"username": "noah", "password": "a_good_password"}'
curl -X POST localhost:8000/tasks -H "content-type: application/json" -H "Authorization: Bearer <your token>" -d '{"url": "https://example.com"}'
curl localhost:8000/tasks -H "Authorization: Bearer <your token>"
```

## What does the real worker need to do?

Four things, and `fake_worker.py` does all four if you want to see them in code. The worker doesn't log in or touch the API at all, it only talks to Redis.

1. Wait for a task id with `BLMOVE task_queue tasks_running RIGHT LEFT 2`. That takes an id off the queue and puts it in `tasks_running` in one step. It gives back nothing if 2 seconds go by with no task, so ask again in a loop.
2. `GET task:<id>`, set `status` to `running`, `active_agent` to its own name and `started_at` to the time, add 1 to `attempts`, and `SET` it back.
3. When it's done, set `status` to `completed` and fill in `result` (or `failed` and fill in `error`), set `completed_at`, and `SET` it back. For a screenshot, also save the PNG as base64 text with `SET task_screenshot:<id> <base64 text> EX 86400`.
4. Take the id back out with `LREM tasks_running 0 <id>`.

A task is saved as plain JSON text, so this works from any language that has a Redis library.

## How do I run the tests?

Run `pytest` from this folder. The tests use fakeredis (a pretend Redis that lives in memory), so Redis doesn't have to be running.

## What's in each file?

| File | What's in it |
|---|---|
| `app.py` | The endpoints. |
| `task_store.py` | Everything that reads or writes tasks and screenshots in Redis. |
| `user_store.py` | Accounts, password hashing and login tokens. |
| `stuck_task_checker.py` | Puts tasks back on the queue when their worker died. |
| `make_admin.py` | Turns an account into an admin. |
| `fake_worker.py` | The pretend worker (`fake_screenshot.png` is the picture it uses). |
| `test_backend.py` | The tests. |

## What isn't built yet?

A Dockerfile, which the API and the checker will each need before they can run in Kubernetes.

Logging out. A token just stops working after a day.

Anything that stops someone from guessing passwords over and over.
