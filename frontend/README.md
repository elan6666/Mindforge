# Mindforge Frontend

Phase 6 turns the previous frontend placeholder into a runnable Web App shell.

Current responsibilities:

- provide a Codex/OpenHands-inspired workspace shell
- let users launch tasks through the existing backend API
- show session history, task controls, final output, orchestration stages, and task metadata

Local development:

```powershell
cd frontend
npm install
npm run dev
```

Default API base URL:

- `http://127.0.0.1:8000/api`

Override with:

```powershell
$env:VITE_API_BASE_URL="http://127.0.0.1:8000/api"
```
