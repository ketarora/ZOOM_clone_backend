.PHONY: install dev seed lint typecheck test clean

VENV   := .venv
PYTHON := $(VENV)/bin/python
PIP    := $(VENV)/bin/pip

# ── Environment ──────────────────────────────────────────────────────────────

$(VENV)/bin/activate:
	python3 -m venv $(VENV)

install: $(VENV)/bin/activate
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	cp -n .env.example .env || true
	@echo "✓ Dependencies installed"

# ── Development ───────────────────────────────────────────────────────────────

dev:
	$(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

seed:
	$(PYTHON) seed.py

# ── Code quality ──────────────────────────────────────────────────────────────

lint:
	$(VENV)/bin/ruff check app/ seed.py
	$(VENV)/bin/ruff format --check app/ seed.py

format:
	$(VENV)/bin/ruff format app/ seed.py
	$(VENV)/bin/ruff check --fix app/ seed.py

typecheck:
	$(VENV)/bin/mypy app/

test:
	$(VENV)/bin/pytest -v

# ── Maintenance ───────────────────────────────────────────────────────────────

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache .ruff_cache
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
