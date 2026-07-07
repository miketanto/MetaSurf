.PHONY: setup lint typecheck checks test rebuild

setup:
	pip install -e ".[dev]"

lint:
	ruff check .

typecheck:
	mypy models jobs api ingest db validation scripts

checks:
	python scripts/check_game_neutrality.py
	python scripts/check_determinism.py

test:
	pytest -q

# One-command rebuild of the historical DB (M0 definition of done)
rebuild:
	bash scripts/rebuild.sh
