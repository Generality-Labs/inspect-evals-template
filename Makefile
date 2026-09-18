# MANAGED FILE - Updates pulled from template. See MANAGED_FILES.md

hooks:
	uv run pre-commit install

check:
	@bash tools/run_checks.sh

TEST_ARGS ?=
test:
	GIT_LFS_SKIP_SMUDGE=1 uv run pytest $(TEST_ARGS)

.PHONY: hooks check test
