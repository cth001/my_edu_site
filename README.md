# Web3 Information Aggregator

## Frontend
- Static prototype homepage: `index.html`

## Backend (FastAPI)
- Entry point: `backend/main.py`

### Run locally
```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### API endpoints
- `GET /api/news` with filters:
  - `q`: search keyword
  - `sources`: comma-separated sources (e.g. `CoinDesk,律动`)
  - `categories`: comma-separated categories (e.g. `news,regulatory`)
  - `time_filter`: `1h | 24h | 7d`
  - `sort_by`: `date | relevance | source`
- `GET /api/prices`
- `GET /health`
