.PHONY: lint test release

lint:
	uv run ruff check . --fix --unsafe-fixes
	uv run ruff format .
	uv run ty check . --exclude python_template

test:
	uv run pytest

release:
	@set -e; \
	VERSION="$$(uv version --short)"; \
	if [ -z "$$VERSION" ]; then \
		echo "Unable to determine version via uv version --short."; \
		exit 1; \
	fi; \
	if ! git diff --quiet || ! git diff --cached --quiet; then \
		echo "Working tree is dirty; commit or stash before releasing."; \
		exit 1; \
	fi; \
	make lint; \
	make test; \
	if ! git diff --quiet || ! git diff --cached --quiet; then \
		echo "Working tree changed during lint/test; commit fixes before releasing."; \
		exit 1; \
	fi; \
	if git rev-parse "v$$VERSION" >/dev/null 2>&1; then \
		echo "Tag v$$VERSION already exists."; \
		exit 1; \
	fi; \
	uv build; \
	uvx twine check dist/uniqfunc-"$$VERSION"*; \
	uvx twine upload dist/uniqfunc-"$$VERSION"*; \
	git tag -a "v$$VERSION" -m "v$$VERSION"; \
	git push origin main --tags
