"""
The API, which is the front door of the project.

The dashboard sends tasks here and asks here for results. This file
only handles the web side (reading requests, sending back JSON). The
Redis side is in task_store.py and user_store.py.

Run it with:  uvicorn app:app --reload
Then open http://localhost:8000/docs to try each endpoint in a browser.
"""

import redis
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from pydantic import BaseModel

import task_store
import user_store

app = FastAPI(title="344 final project backend")

# Browsers block a page from calling an API on a different address unless
# the API says it's allowed. The dashboard is served from a different
# address than this API, so this allows it.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# After logging in, the dashboard sends its token with every request in
# a header that looks like "Authorization: Bearer <token>". This reads it.
bearer = HTTPBearer(auto_error=False)


def current_user(credentials=Depends(bearer)):
    """
    Works out who is asking, from the token they sent. Any endpoint with
    user=Depends(current_user) runs this first, so it needs a login.
    """
    token = credentials.credentials if credentials else ""
    user = user_store.get_user_for_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="log in first")
    return user


class UsernameAndPassword(BaseModel):
    """What the dashboard sends to make an account or to log in."""

    username: str
    password: str


class NewTask(BaseModel):
    """What the dashboard sends to submit a task."""

    url: str
    task_type: str = "screenshot"


@app.get("/health")
def health():
    """A quick check that the API is up and can reach Redis."""
    try:
        tasks_waiting = task_store.tasks_waiting()
        tasks_running = task_store.tasks_running()
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="can't reach redis")
    return {
        "status": "ok",
        "tasks_waiting": tasks_waiting,
        "tasks_running": tasks_running,
    }


@app.post("/users", status_code=201)
def create_user(new_user: UsernameAndPassword):
    """Makes a new account. Everyone starts at permission level 0."""
    username = new_user.username
    if not 3 <= len(username) <= 32 or not username.replace("_", "").isalnum():
        raise HTTPException(
            status_code=400,
            detail="username has to be 3 to 32 letters, numbers or underscores",
        )
    # bcrypt (what we hash passwords with) only reads the first 72 bytes.
    if not 8 <= len(new_user.password.encode()) <= 72:
        raise HTTPException(
            status_code=400,
            detail="password has to be 8 to 72 characters",
        )
    user = user_store.create_user(username, new_user.password)
    if user is None:
        raise HTTPException(status_code=400, detail="that username is taken")
    return user_store.public_user(user)


@app.post("/login")
def login(attempt: UsernameAndPassword):
    """Checks a username and password and hands back a token."""
    user = user_store.check_login(attempt.username, attempt.password)
    if user is None:
        raise HTTPException(status_code=401, detail="wrong username or password")
    return {
        "token": user_store.create_token(user),
        "user": user_store.public_user(user),
    }


@app.post("/tasks", status_code=201)
def submit_task(new_task: NewTask, user=Depends(current_user)):
    """Saves a new task, puts it on the queue, and returns it."""
    if not new_task.url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="url has to start with http:// or https://",
        )
    if new_task.task_type not in task_store.TASK_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"task_type has to be one of {task_store.TASK_TYPES}",
        )
    return task_store.create_task(new_task.url, new_task.task_type, user["id"])


@app.get("/tasks")
def list_tasks(user=Depends(current_user)):
    """Your most recent tasks, newest first. An admin gets everyone's."""
    if user_store.is_admin(user):
        return task_store.list_tasks()
    return task_store.list_tasks(user["id"])


@app.get("/tasks/{task_id}")
def get_task(task_id: str, user=Depends(current_user)):
    """One task. The dashboard calls this over and over to watch its status."""
    task = task_store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="no task with that id")
    # Somebody else's task looks the same as one that doesn't exist.
    if task["user_id"] != user["id"] and not user_store.is_admin(user):
        raise HTTPException(status_code=404, detail="no task with that id")
    return task


@app.get("/tasks/{task_id}/screenshot")
def get_screenshot(task_id: str):
    """
    The screenshot for a task, as a PNG image.

    This one doesn't need a login, since an <img> tag on the dashboard
    can't send a token. The task id is a long random string that nobody
    can guess, and that's what keeps other people out.
    """
    image_bytes = task_store.get_screenshot(task_id)
    if image_bytes is None:
        raise HTTPException(status_code=404, detail="no screenshot for that task")
    return Response(content=image_bytes, media_type="image/png")
