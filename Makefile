# MANAGED FILE - Updates pulled from template. See MANAGED_FILES.md
hooks:
	uv run pre-commit install

check:
	@bash tools/run_checks.sh

# Add extras or dependency groups your tests need, e.g.
#   make test TEST_EXTRAS=my_eval TEST_GROUPS=my_group TEST_ARGS="-k not agentic"
TEST_ARGS ?=
TEST_EXTRAS ?=
TEST_GROUPS ?=
test:
	GIT_LFS_SKIP_SMUDGE=1 uv run \
		$(addprefix --extra ,$(TEST_EXTRAS)) \
		$(addprefix --group ,$(TEST_GROUPS)) \
		pytest $(TEST_ARGS)

.PHONY: hooks check test
