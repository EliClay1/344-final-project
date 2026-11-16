# CYBER 344 frontend

Vue dashboard for the FastAPI browser task service.

## Run locally

```sh
npm install
npm run dev
```

Copy `.env.example` to `.env` to use the real API. The API must be running at `http://localhost:8000`; change `VITE_API_BASE_URL` if it runs elsewhere. Restart Vite after changing `.env`.

Set `VITE_USE_MOCK=true` for the standalone demo. The mock login offers `dixon` and `admin`, both with password `password123`. Mock accounts and tasks stay in memory and reset when the page reloads.

For the real API, run Noah's backend with Redis and a worker (the fake worker is sufficient for a local demo). Register an account in the dashboard; registration creates the user through `POST /users` and then signs in through `POST /login`. Accounts start with permission level 0. To test the admin view, promote an account with the backend's `make_admin.py` utility and sign in again.

The real admin view shows the most recent 50 tasks from `GET /tasks`. The backend has no log endpoint yet, so the sample log panel appears only in mock mode. Screenshots are loaded from `GET /tasks/{id}/screenshot` and expire after one day.

```sh
npm run build
```
