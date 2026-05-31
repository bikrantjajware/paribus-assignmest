# Hospital Bulk Upload API

A Flask REST API that accepts a CSV file of hospital records, validates and persists each row via an external Hospital Directory API, triggers a batch-activation call, and exposes a polling endpoint to check batch processing status.

---

## Features

- **Bulk CSV Upload** — `POST /hospitals/bulk` accepts a multipart CSV file and processes every row in one shot.
- **Row-level Validation** — Each row is validated with Pydantic; invalid rows are collected into a structured error list without aborting the whole batch.
- **In-Memory Store** — Successfully created hospitals are mirrored into a process-level in-memory store (`DBHospital` / `HOSPITALS` dict) for fast local reads.
- **External API Client** — A thin `HospitalAPIClient` wrapper (using `requests.Session`) communicates with the upstream Hospital Directory service for hospital creation and batch activation.
- **Batch Activation** — After all valid rows are persisted remotely, a single `PATCH /hospitals/batch/{batch_id}/activate` call activates the entire batch; the in-memory store is updated to reflect this.
- **Structured Response** — The endpoint returns a JSON summary with batch ID, counts, per-hospital statuses, processing time, and activation flag.
- **Batch Status Polling** — `GET /hospitals/bulk/{batch_id}` (or `GET /hospitals/bulk` to query the most-recent batch) returns real-time progress from the in-memory `BatchStore`.
- **Health Check** — `GET /health` for liveness probing.

---

## Tech Stack

| Layer           | Technology                                                            |
| --------------- | --------------------------------------------------------------------- |
| Web Framework   | [Flask 3.x](https://flask.palletsprojects.com/)                       |
| Data Validation | [Pydantic v2](https://docs.pydantic.dev/latest/)                      |
| HTTP Client     | [Requests](https://requests.readthedocs.io/) (via `requests.Session`) |
| WSGI Server     | [Gunicorn](https://gunicorn.org/)                                     |
| Config          | [python-dotenv](https://pypi.org/project/python-dotenv/)              |
| Runtime         | Python 3.12+                                                          |

---

## Design Decisions

### Separation of Concerns (layered architecture)

`routes.py` only handles HTTP requests (file presence, content-type guard, error-to-status mapping). All business logic lives in `services/hospital_service.py`, making the service testable in isolation without spinning up a Flask test client.

### Pydantic v2 for validation

Pydantic's `model_validate` checks each CSV row, automatically converts values, shows clear errors, and keeps the data format defined in one place.

### Partial-failure model

Invalid CSV rows are collected into a `RowError` and skipped, allowing all valid rows to be processed without stopping the request.

### `requests.Session` for the API client

Using a shared `Session` object enables HTTP keep-alive connection pooling across multiple rows in a single batch, reducing TCP overhead compared to individual `requests.get/post` calls.

### Flask Application Factory

`create_app()` follows the Flask application factory pattern, which makes it straightforward to instantiate the app with different configs (e.g., test vs. production) and avoids circular import issues.

### Consistent response shape for status polling

`GET /hospitals/bulk/{batch_id}` returns the exact same `BulkUploadResponse` schema as
`POST /hospitals/bulk`. This means callers can poll for progress without needing to handle a separate response model — the same deserialization code works for both endpoints.

---

## Project Structure

```
paribus-assignment/
├── app/
│   ├── __init__.py              # App factory (create_app), blueprint registration
│   ├── extensions.py            # Singleton HospitalAPIClient instance
│   ├── hospital_api_client.py   # External API client (create, activate, CRUD)
│   ├── db.py                    # In-memory store — DBHospital + HOSPITALS dict, BatchStore for status polling
│   ├── schemas.py               # Pydantic schemas (HospitalRow, BulkUploadResponse, …)
│   ├── routes.py                # Blueprint — request/response layer only
│   ├── services/
│   │   ├── __init__.py
│   │   └── hospital_service.py  # Business logic: orchestrates parse → persist → activate → status polling
│   └── utils/
│       ├── file_utils.py        # Generic CSV parsing + Pydantic row validation
│       └── hospital_utils.py    # Hospital-specific helpers (wraps client + DB write)
├── requirements.txt
├── .env                         # Environment variables (see Setup)
└── README.md
```

### Layer Responsibilities

```
routes.py               →  HTTP boundary (request parsing, error → HTTP status mapping)
services/               →  Use-case orchestration (parse CSV → create hospitals → activate batch → status polling)
utils/                  →  Reusable helpers (CSV parsing, external API ↔ local DB bridge)
hospital_api_client.py  →  External HTTP calls (single responsibility)
db.py                   →  In-memory persistence model + BatchStore for batch tracking
schemas.py              →  Shared data contracts (input + output)
```

---

## Setup — Run Locally

### Prerequisites

- Python 3.12+
- `pip` (or `pip3`)

### 1. Clone & create a virtual environment

```bash
git clone <repo-url>
cd paribus-assignment

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the example below into a `.env` file at the project root:

```env
HOSPITAL_API_BASE_URL=https://hospital-directory.onrender.com
```

| Variable                | Description                                     |
| ----------------------- | ----------------------------------------------- |
| `HOSPITAL_API_BASE_URL` | Base URL of the upstream Hospital Directory API |

### 4. Run the development server

```bash
python -m flask run
```

The API will be available at `http://127.0.0.1:5000`.

### 5. (Optional) Run with Gunicorn

```bash
gunicorn app:app -b 0.0.0.0:8080 -w 2
```

---

## API Reference

### `POST /hospitals/bulk`

Upload a CSV file to bulk-create and activate hospitals.

**Request** — multipart/form-data

| Field  | Type        | Required | Description                                                  |
| ------ | ----------- | -------- | ------------------------------------------------------------ |
| `file` | `.csv` file | ✅       | CSV with columns `name`, `address`, `phone` (phone optional) |

**CSV format**

```csv
name,address,phone
appolo,blr street a,123
ruby hospital,em by pass road,122
```

**Success Response** — `200 OK`

```json
{
  "batch_activated": true,
  "batch_id": "1a83c86e-0b29-41a0-8a4b-5444929d6906",
  "failed_hospitals": 1,
  "hospitals": [
    {
      "hospital_id": 26,
      "name": "appolo",
      "row": 1,
      "status": "created_and_activated"
    },
    {
      "hospital_id": 27,
      "name": "ruby hospital",
      "row": 3,
      "status": "created_and_activated"
    }
  ],
  "processed_hospitals": 2,
  "processing_time_seconds": 11,
  "total_hospitals": 3
}
```

**Error Responses**

| Status | Cause                                          |
| ------ | ---------------------------------------------- |
| `400`  | Missing file, empty CSV, or no valid data rows |
| `415`  | Uploaded file is not a CSV                     |
| `500`  | Upstream API or persistence failure            |

---

### `GET /hospitals/bulk` · `GET /hospitals/bulk/{batch_id}`

Poll the processing status of a batch. Both routes return the **same response shape** as `POST /hospitals/bulk`, making it easy to poll for progress without any additional parsing logic.

- **`GET /hospitals/bulk/{batch_id}`** — Query a specific batch by its UUID.
- **`GET /hospitals/bulk`** — Query the most-recently started batch (convenience shortcut; resolves via `BatchStore.get_current()`).

**Path Parameter**

| Parameter  | Type   | Required | Description                                                              |
| ---------- | ------ | -------- | ------------------------------------------------------------------------ |
| `batch_id` | string | ❌       | UUID returned by `POST /hospitals/bulk`. Omit to query the latest batch. |

**Success Response** — `200 OK`

```json
{
  "batch_id": "1a83c86e-0b29-41a0-8a4b-5444929d6906",
  "total_hospitals": 3,
  "processed_hospitals": 2,
  "failed_hospitals": 1,
  "processing_time_seconds": 11,
  "batch_activated": true,
  "hospitals": [
    {
      "row": 1,
      "hospital_id": 26,
      "name": "appolo",
      "status": "created_and_activated"
    }
  ]
}
```

**Error Responses**

| Status | Cause                                                       |
| ------ | ----------------------------------------------------------- |
| `400`  | No `batch_id` provided and no batch is currently processing |
| `404`  | No batch found for the given `batch_id`                     |

---

### `GET /health`

Liveness check — returns `{"status": "ok"}` with `200 OK`.

---

## Future Improvements

- **Unit & integration tests** — Add a `pytest` test suite covering:
  - `parse_csv_upload` with valid/invalid/empty CSVs
  - `process_bulk_upload` with mocked `hospital_utils` calls
  - Route-level tests using Flask's test client
  - `HospitalAPIClient` with `responses` or `httpretty` for HTTP mocking

- **Dockerize the application** — Add a `Dockerfile` and `docker-compose.yml` so the service (and a mock upstream) can be spun up with a single command:

  ```dockerfile
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8080", "-w", "2"]
  ```

- **Persistent database** — Replace the in-memory `HOSPITALS` dict with SQLAlchemy + PostgreSQL/SQLite so data survives process restarts.

- **Async / concurrent processing** — Use `asyncio` + `aiohttp` (or a task queue like Celery) to fire external API calls concurrently instead of sequentially, significantly reducing total processing time for large batches.

- **Pagination & querying** — Expose `GET /hospitals` with cursor-based pagination and filters (by batch, status, name).

- **Authentication & rate limiting** — Add API-key or JWT authentication and per-client rate limiting via Flask-Limiter.

- **OpenAPI / Swagger docs** — Auto-generate API documentation from the Pydantic schemas using `flask-openapi3` or `apiflask`.
