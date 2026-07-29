# Contributing to OpsFlow AI

Thanks for improving OpsFlow AI. Keep changes focused and portfolio-quality.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
pytest -q
```

## Guidelines

1. Prefer small, reviewable PRs with a clear “why”.
2. Match existing module layout (`api` / `agents` / `rag` / `services`).
3. Do not commit `.env`, credentials, or uploaded documents.
4. Add or update tests for behaviour changes.
5. Keep offline demos working when `OPENAI_API_KEY` is unset.
6. Document any new env vars in `.env.example`.

## Useful commands

```bash
uvicorn backend.main:app --reload --port 8000
streamlit run frontend/streamlit_app.py
pytest -q --cov=backend
```

## Agent / automation notes

- LangGraph router (`build_langgraph_router`) is optional / experimental.
- n8n workflows under `automation/n8n_workflows/` must be imported manually into n8n.
- Welcome emails are **drafted** by OpsFlow; SMTP send happens in n8n when configured.
