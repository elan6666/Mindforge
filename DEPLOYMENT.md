# Mindforge Deployment

Mindforge is split into two deployable parts:

- Frontend: React/Vite static site, deployed on Vercel.
- Backend: FastAPI API service, deployed on Render.

## Privacy rule

Never commit real API keys or local data. The repository ignores `.env*`,
`app/model_control/provider_secrets.json`, SQLite databases, uploaded files,
artifacts, local workspaces, and generated outputs.

## Backend on Render

Use the `render.yaml` Blueprint in this repository.

Required environment variables in Render:

- `CORS_ORIGINS`: JSON array of allowed frontend origins, for example
  `["https://your-vercel-project.vercel.app"]`
- `ARK_API_KEY`: Volces Ark API key, if using Ark models.
- `DEEPSEEK_API_KEY`: DeepSeek API key, if using DeepSeek.
- `OPENAI_API_KEY`: OpenAI API key, if using OpenAI catalog models.
- `MOONSHOT_API_KEY`: Moonshot/Kimi API key, if using Moonshot.
- `ZHIPU_API_KEY`: Zhipu/GLM API key, if using GLM.

Only fill the keys in the Render dashboard. Do not write them into files.

## Frontend on Vercel

The root `vercel.json` builds the `frontend/` app and publishes
`frontend/dist`.

Set this Vercel environment variable after the Render backend exists:

- `VITE_API_BASE_URL=https://your-render-service.onrender.com/api`

Then redeploy the Vercel project.

## Local smoke checks

```bash
python -m pytest
cd frontend
npm run test
npm run build
```
