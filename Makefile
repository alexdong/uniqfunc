.PHONY: dev test 

dev:
	uv run ruff check . --fix --unsafe-fixes
	uv run ruff format .
	uv run ty check . --exclude python_template

test:
	uv run pytest --lf
