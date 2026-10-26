.PHONY: install lint format typecheck test check

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy mcp_tdo

test:
	pytest

check: lint typecheck test
