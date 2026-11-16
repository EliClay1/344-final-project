"""
The browser worker.

The worker never talks to the API, only to Redis. If it dies partway
through a task, the id is still in tasks_running, and the backend's
stuck_task_checker.py puts it back on the queue after 60 seconds. That's
why the worker has to finish every task well under 60 seconds
(TASK_LIMIT_SECONDS below).

To run, use either of these commands:

This requires Redis active
python worker.py

This one runs on it's own with a list of test tasks.
python worker.py --local sample_tasks.json
"""

import argparse
import asyncio
import base64
import ipaddress
import json
import os
import signal
import socket
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeout
from playwright.async_api import async_playwright

# ---- environment variable settings ----

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
AGENT_NAME = os.environ.get("AGENT_NAME", socket.gethostname())
PAGE_LOAD_SECONDS = float(os.environ.get("PAGE_LOAD_SECONDS", 15))

# The most time a whole task gets, start to finish. It has to stay under
# the backend's TASK_TIMEOUT_SECONDS (60) or the stuck task checker would
# give the task to a second worker while this one is still on it.
TASK_LIMIT_SECONDS = float(os.environ.get("TASK_LIMIT_SECONDS", 40))
STUCK_CHECKER_SECONDS = 60
TASKS_PER_BROWSER = int(os.environ.get("TASKS_PER_BROWSER", 50))

# The size of the screenshot, and whether to capture the whole page.
SCREEN_WIDTH = int(os.environ.get("SCREEN_WIDTH", 1280))
SCREEN_HEIGHT = int(os.environ.get("SCREEN_HEIGHT", 800))
FULL_PAGE = os.environ.get("FULL_PAGE", "false") == "true"

# Only for testing
ALLOW_PRIVATE_URLS = os.environ.get("ALLOW_PRIVATE_URLS", "false") == "true"

CHROMIUM_SANDBOX = os.environ.get("CHROMIUM_SANDBOX", "false") == "true"
TASK_QUEUE = "task_queue"
TASKS_RUNNING = "tasks_running"
SCREENSHOT_SECONDS = 24 * 60 * 60

# General helper functions
def task_key(task_id):
    return f"task:{task_id}"

def screenshot_key(task_id):
    return f"task_screenshot:{task_id}"
    
def now():
    """The current time in UTC."""
    return datetime.now(timezone.utc).isoformat()

def log(event, **details):
    """One JSON line per event."""
    line = {"time": now(), "agent": AGENT_NAME, "event": event, **details}
    print(json.dumps(line), flush=True)


class TaskFailed(Exception):
    """
    A task that failed for a reason the worker understands.
    The value returned here is safe for the frontend.
    """

    def __init__(self, kind, message):
        super().__init__(f"{kind}: {message}")
        self.kind = kind


def explain(error):
    """ 
    Takes a given error and will check if it's one recognizable. 
    If not, then it will do a general parsing sweep
    """

    if isinstance(error, TaskFailed):
        return error
    
    if isinstance(error, (PlaywrightTimeout, asyncio.TimeoutError, TimeoutError)):
        return TaskFailed("timeout", f"the page took longer than {PAGE_LOAD_SECONDS:g} seconds to load")
    
    text = str(error)
    first_line = text.splitlines()[0] if text else type(error).__name__

    if "ERR_BLOCKED_BY_CLIENT" in text:
        return TaskFailed("blocked", "the page tried to reach a private address")
    if "ERR_NAME_NOT_RESOLVED" in text:
        return TaskFailed("dns", "that website's name doesn't exist")
    if "ERR_CONNECTION_REFUSED" in text:
        return TaskFailed("connection", "the website refused the connection")
    if "ERR_CERT" in text or "SSL" in text:
        return TaskFailed("tls", "the website's security certificate is bad")
    if "net::ERR_" in text:
        return TaskFailed("network", first_line)
    if "closed" in text.lower() or "crash" in text.lower():
        return TaskFailed("browser_crash", "the browser crashed while loading the page")

    # General error return statement.
    return TaskFailed("worker_error", f"{type(error).__name__}: {first_line}")




async def check_host(host, port):
    """
    Checks if the attempted URL is a host address

    Without this, someone could submit something like http://redis:6379 and get a screenshot of
    something inside the cluster.
    """

    if ALLOW_PRIVATE_URLS:
        return
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(host, port)
    except socket.gaierror:
        raise TaskFailed("dns", "that website's name doesn't exist")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0].split("%")[0])
        if not ip.is_global:
            raise TaskFailed("blocked", f"{host} is a private address")


async def check_url(url):
    """
    Basic check to see if the url is a valid URL or not.
    Frontend and backend should handle most of this, but I figured it should be put anyways.
    """
    parts = urlparse(url or "")
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise TaskFailed("bad_url", "url has to start with http:// or https://")
    await check_host(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))


async def block_private_requests(route):
    """Runs on every request the page makes (images, scripts, ...)."""
    parts = urlparse(route.request.url)
    if parts.hostname and not ALLOW_PRIVATE_URLS:
        try:
            await check_host(parts.hostname, parts.port or (443 if parts.scheme in ("https", "wss") else 80))
        except TaskFailed:
            log("request_blocked", url=route.request.url[:200])
            return await route.abort("blockedbyclient")
    await route.continue_()

class Browser:
    """One Chromium for the whole worker. Each task gets its own fresh tab."""

    def __init__(self, playwright):
        self.playwright = playwright
        self.chromium = None
        self.tasks_done = 0

    async def get(self):
        if self.chromium is None or not self.chromium.is_connected():
            await self.restart("starting" if self.chromium is None else "it disconnected")
        elif self.tasks_done >= TASKS_PER_BROWSER:
            await self.restart(f"it did {TASKS_PER_BROWSER} tasks")
        self.tasks_done += 1
        return self.chromium

    async def restart(self, reason):
        await self.close()
        started = time.monotonic()
        self.chromium = await self.playwright.chromium.launch(
            headless=True,
            chromium_sandbox=CHROMIUM_SANDBOX,
            # /dev/shm is tiny in containers, so Chromium uses /tmp instead
            args=["--disable-dev-shm-usage", "--disable-gpu", "--no-first-run", "--mute-audio"],
        )
        self.tasks_done = 0
        log("browser_started", reason=reason, took_ms=round((time.monotonic() - started) * 1000))

    async def close(self):
        if self.chromium is not None:
            try:
                await asyncio.wait_for(self.chromium.close(), 10)
            except Exception as error:
                log("browser_close_failed", error=str(error)[:200])
            self.chromium = None


async def open_page(page, url, wait_until):
    started = time.monotonic()
    response = await page.goto(url, wait_until=wait_until, timeout=PAGE_LOAD_SECONDS * 1000)
    load_time_ms = round((time.monotonic() - started) * 1000)
    # Redirects skip the check in block_private_requests, so check where we ended up.
    final = urlparse(page.url)
    if final.hostname:
        await check_host(final.hostname, final.port or (443 if final.scheme == "https" else 80))
    return response, load_time_ms


# Any additional task types will be added in this section.

async def availability_check(page, task):
    """
    The core functionality of checking site availability.
    Returns a JSON object.
    """
    response, load_time_ms = await open_page(page, task["url"], "domcontentloaded")
    http_status = response.status if response else None
    result = {
        "is_up": http_status is not None and http_status < 400,
        "http_status": http_status,
        "load_time_ms": load_time_ms,
        # Extras.
        "page_title": (await page.title())[:300],
        "final_url": page.url,
    }
    return result, None


async def screenshot(page, task):
    """
    The core functionality of the screenshot feature.
    Returns a JSON object.
    """
    response, load_time_ms = await open_page(page, task["url"], "load")
    try:
        # Give late images a moment, but don't wait forever on busy pages.
        await page.wait_for_load_state("networkidle", timeout=3000)
    except PlaywrightTimeout:
        pass
    image_bytes = await page.screenshot(full_page=FULL_PAGE, timeout=PAGE_LOAD_SECONDS * 1000)
    result = {
        # Same key as fake_worker.py.
        "page_title": (await page.title())[:300],
        # Extras.
        "http_status": response.status if response else None,
        "load_time_ms": load_time_ms,
        "final_url": page.url,
        "screenshot_bytes": len(image_bytes),
    }
    return result, image_bytes


TASK_TYPES = {"availability_check": availability_check, "screenshot": screenshot}


async def run_in_browser(browser, task):
    """Returns (result, image_bytes or None). Raises if anything goes wrong."""

    # Checks if the task is valid or not.
    do_task = TASK_TYPES.get(task.get("task_type"))
    if do_task is None:
        raise TaskFailed("bad_task", f"unknown task_type {task.get('task_type')!r}")
    await check_url(task.get("url"))

    # Takes the attached browser parameter and activates the 
    # browser functionality dependent on the task.
    chromium = await browser.get()
    context = await chromium.new_context(
        viewport={"width": SCREEN_WIDTH, "height": SCREEN_HEIGHT},
        accept_downloads=False,
        service_workers="block",
    )

    try:
        if not ALLOW_PRIVATE_URLS:
            await context.route("**/*", block_private_requests)
        page = await context.new_page()
        return await do_task(page, task)
    
    finally:
        try:
            await asyncio.wait_for(context.close(), 5)
        except Exception:
            await browser.restart("a tab wouldn't close")


async def do_task_safely(browser, task):
    """Returns (result, image_bytes, error_text). Never raises."""

    started = time.monotonic()

    try:
        result, image_bytes = await asyncio.wait_for(run_in_browser(browser, task), TASK_LIMIT_SECONDS)
        log("task_completed", task_id=task.get("id"), task_type=task.get("task_type"),
            took_ms=round((time.monotonic() - started) * 1000))
        return result, image_bytes, None
    
    except Exception as error:
        failure = explain(error)
        if failure.kind == "browser_crash":
            await browser.restart("it crashed")

        log("task_failed", task_id=task.get("id"), task_type=task.get("task_type"), kind=failure.kind,
            error=str(failure), took_ms=round((time.monotonic() - started) * 1000))
        return None, None, str(failure)

async def work_on(redis_client, browser, task_id):

    # mark the task as running once the worker recieves it.
    saved = await redis_client.get(task_key(task_id))
    if saved is None:
        # wipe the task id if Redis already removed it.
        await redis_client.lrem(TASKS_RUNNING, 0, task_id)
        log("task_missing", task_id=task_id)
        return

    # Load the task up
    task = json.loads(saved)
    if task["status"] in ("completed", "failed"):
        await redis_client.lrem(TASKS_RUNNING, 0, task_id)
        return
    task["status"] = "running"
    task["active_agent"] = AGENT_NAME
    task["started_at"] = now()
    task["attempts"] += 1
    await redis_client.set(task_key(task_id), json.dumps(task))
    my_start = task["started_at"]

    # run the browser and return the necessary data from it.
    result, image_bytes, error = await do_task_safely(browser, task)

    # If we somehow went over 60 seconds, the stuck task checker may have
    # handed this task to another worker. Then it's theirs, so we drop ours.
    latest = json.loads(await redis_client.get(task_key(task_id)) or "null")
    if latest is None or latest.get("active_agent") != AGENT_NAME or latest.get("started_at") != my_start:
        log("task_taken_over", task_id=task_id)
        return

    if image_bytes is not None:
        image_text = base64.b64encode(image_bytes).decode()
        await redis_client.set(screenshot_key(task_id), image_text, ex=SCREENSHOT_SECONDS)
    latest["status"] = "completed" if error is None else "failed"
    latest["result"] = result
    latest["error"] = error
    latest["completed_at"] = now()
    await redis_client.set(task_key(task_id), json.dumps(latest))


    await redis_client.lrem(TASKS_RUNNING, 0, task_id)


async def run_with_redis(stop):
    import redis.asyncio as redis

    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    await redis_client.ping()
    log("worker_started", redis=REDIS_URL)
    async with async_playwright() as playwright:
        browser = Browser(playwright)
        try:
            while not stop.is_set():
                # Step 1: wait up to 2 seconds for a task id, then ask again.
                # This is also how often we notice a request to shut down.
                task_id = await redis_client.blmove(TASK_QUEUE, TASKS_RUNNING, 2, "RIGHT", "LEFT")
                if task_id is not None:
                    await work_on(redis_client, browser, task_id)
        finally:
            await browser.close()
            await redis_client.aclose()
            log("worker_stopped")

async def run_locally(file_name, stop):
    with open(file_name) as tasks_file:
        tasks = json.load(tasks_file)
    os.makedirs("screenshots", exist_ok=True)
    async with async_playwright() as playwright:
        browser = Browser(playwright)
        try:
            for number, task in enumerate(tasks):
                if stop.is_set():
                    break
                task.setdefault("id", f"local-{number}")
                task.setdefault("task_type", "screenshot")
                result, image_bytes, error = await do_task_safely(browser, task)
                if image_bytes is not None:
                    with open(f"screenshots/{task['id']}.png", "wb") as image_file:
                        image_file.write(image_bytes)
                status = "completed" if error is None else "failed"
                print(json.dumps({"id": task["id"], "url": task["url"], "status": status,
                                  "result": result, "error": error}, indent=2), flush=True)
        finally:
            await browser.close()


def main():
    # Adds command line parsing descriptors for instruction on what parameters should be.
    parser = argparse.ArgumentParser(description="the browser worker")
    parser.add_argument("--local", metavar="TASKS_JSON", help="run the tasks in this file instead of using Redis")
    
    # Parses the attached arguments.
    args = parser.parse_args()

    if TASK_LIMIT_SECONDS + 10 >= STUCK_CHECKER_SECONDS:
        sys.exit(f"TASK_LIMIT_SECONDS has to be under {STUCK_CHECKER_SECONDS - 10}, "
                 "or the stuck task checker will take tasks away from working workers")

    async def start():
        # Kubernetes sends SIGTERM when it scales a worker down. We finish the
        # task we're on (Kubernetes gives us terminationGracePeriodSeconds),
        # then stop asking for new ones.
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for signal_type in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(signal_type, lambda s=signal_type: (log("stopping", signal=s.name), stop.set()))
        if args.local:
            await run_locally(args.local, stop)
        else:
            await run_with_redis(stop)

    asyncio.run(start())


if __name__ == "__main__":
    main()
