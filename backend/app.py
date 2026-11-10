"""
The API, which is the front door of the project.

The dashboard sends tasks here and asks here for results. This file
only handles the web side (reading requests, sending back JSON). The
Redis side is in task_store.py.

Run it with:  uvicorn app:app --reload
Then open http://localhost:8000/docs to try each endpoint in a browser.
"""

import redis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import task_store

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


class NewTask(BaseModel):
    """What the dashboard sends to submit a task."""

    url: str
    task_type: str = "screenshot"


@app.get("/health")
def health():
    """A quick check that the API is up and can reach Redis."""
    try:
        tasks_waiting = task_store.tasks_waiting()
    except redis.RedisError:
        raise HTTPException(status_code=503, detail="can't reach redis")
    return {"status": "ok", "tasks_waiting": tasks_waiting}


@app.post("/tasks", status_code=201)
def submit_task(new_task: NewTask):
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
    return task_store.create_task(new_task.url, new_task.task_type)


@app.get("/tasks")
def list_tasks():
    """The most recent tasks, newest first."""
    return task_store.list_tasks()


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    """One task. The dashboard calls this over and over to watch its status."""
    task = task_store.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="no task with that id")
    return task
