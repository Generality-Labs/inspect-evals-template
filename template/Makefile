check:
	uv run ruff check
	uv run ruff format --check
	uv run basedpyright src tests
	uv run inspect-evals-lint --all
	uv run inspect-evals-readmes generate --check
	uv run pre-commit run --all-files

test:
	uv run pytest

readmes:
	uv run inspect-evals-readmes generate

hooks:
	uv run pre-commit install

.PHONY: check test readmes hooks
