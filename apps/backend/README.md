# SQA KB · Backend

FastAPI app — Fase 5 entrega solo el esqueleto. La implementación del dominio,
RAG, ingesta y agente vienen en fases 1-4 del ROADMAP (numeración de fases del
backend reordenada respecto del frontend).

## Arrancar local

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"
uvicorn sqa_kb.main:app --reload --port 8000
```

Abrí http://localhost:8000/docs

## Tests

```bash
pytest -q
```
