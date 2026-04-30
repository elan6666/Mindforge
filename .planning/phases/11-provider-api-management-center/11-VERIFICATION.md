# Phase 11 Verification: Provider API Management Center

## Verification Goal

Prove that provider configuration can be viewed, edited, tested, and consumed by runtime execution while preserving API key secrecy. A Phase 11 release cannot pass if any command output, API response, UI surface, committed file, or log reveals a plaintext API key.

## Required Local Setup

Install backend and frontend dependencies before running verification:

```powershell
python -m pip install -e .[dev]
cd .\frontend
npm install
cd ..
```

Configure live provider keys only in the current shell when live checks are required:

```powershell
$env:OPENHANDS_MODE = "model-api"
$env:ARK_API_KEY = "<your-ark-api-key>"
```

Do not write real secrets into committed files. Provider override files may contain env var names such as `ARK_API_KEY`, but not the key value.

## Automated Test Commands

Run backend tests:

```powershell
python -m pytest -q
```

Run frontend tests:

```powershell
cd .\frontend
npm run test
cd ..
```

Run frontend production build:

```powershell
cd .\frontend
npm run build
cd ..
```

Run Python compile check:

```powershell
python -m compileall app
```

## Local Startup Commands

Start the backend:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local_demo.ps1
```

Equivalent direct backend command:

```powershell
$env:PYTHONPATH = (Resolve-Path ".").Path
python -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Start the frontend in a second shell:

```powershell
cd .\frontend
npm run dev
```

Default local URLs:

```text
Backend: http://127.0.0.1:8000
Frontend: http://127.0.0.1:5173
API base: http://127.0.0.1:8000/api
```

## Manual QA Checklist

| Check | Steps | Expected Result |
| --- | --- | --- |
| Provider list | Open Provider/API Center | All catalog providers appear with enabled state, protocol, base URLs, env var name, and configured/missing key state |
| No secret display | Inspect Provider/API Center and browser devtools | No plaintext key, masked key fragment, Authorization header, or bearer token is visible |
| Edit provider | Change non-secret provider fields and save | Backend persists override and refreshed UI shows the effective values |
| Missing key test | Clear the provider key env var and run connection test | UI reports missing/unconfigured key without showing a secret value |
| Configured key test | Set key env var and run connection test | UI reports pass/fail/upstream status without showing the key value |
| Runtime handoff | Submit a task using a model from the edited provider | Adapter uses effective provider config and task metadata remains secret-free |
| Regression | Open model control, rule templates, history, and paper revision flow | Existing Phase 7-10 behavior remains functional |

## API Smoke Checks

Use these checks after the backend starts:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/api/health
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/api/providers
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/api/control/models
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/api/control/rule-templates
```

Phase 11 provider-control smoke checks:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/api/control/providers
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/control/providers/volces-ark/test
```

## Secret Hygiene Checks

Before release, inspect the working tree and generated files:

```powershell
git status --short
git diff -- . ':!frontend/package-lock.json'
```

Targeted manual review must confirm:

- No real API key value appears in tracked files, snapshots, logs, task metadata, or generated docs.
- API responses include `api_key_configured` and `api_key_env`, but never the env var value.
- Frontend state and tests do not hard-code real provider keys.
- If an ignored secret store is introduced, its path is ignored by git before use.

## Pass/Fail Record

| Command or Check | Required Status | Result |
| --- | --- | --- |
| `python -m pytest -q` | Pass | 59 passed |
| `npm run test` | Pass | 4 passed |
| `npm run build` | Pass | Passed |
| `python -m compileall app` | Pass | Passed |
| Backend startup | Pass | `GET /api/health` returned `{"status":"ok","service":"mindforge"}` |
| Frontend startup | Pass | `GET http://127.0.0.1:5173` returned HTTP 200 |
| Provider/API Center manual QA | Pass | Provider/API Center is available at `http://127.0.0.1:5173` under Models |
| Secret hygiene review | Pass | Targeted grep found no submitted Ark key in tracked source paths |

## Running Local URL

```text
http://127.0.0.1:5173
```

## Release Decision

Do not release Phase 11 until every required command passes and the secret hygiene review is explicitly marked pass. A configured API key is allowed in the local shell for live testing, but any plaintext key in git-tracked files, API output, browser UI, logs, or task history is a release blocker.
