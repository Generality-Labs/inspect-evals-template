#!/usr/bin/env bash
# MANAGED FILE - Updates pulled from template. See MANAGED_FILES.md
#
# Run all repository checks, honouring ENFORCE_<NAME> environment variables.
#
# Each check has a default enforcement mode:
#   - Correctness checks (ruff, mypy, posix, uv lock, unlisted-evals,
#     pytest) default to ENFORCED — failure is a build error.
#   - Standard / opinionated checks (autolint, markdownlint, large-file
#     reporting, generated-doc consistency) default to ADVISORY — failure
#     is reported but does not fail the build.
#
# Override with ENFORCE_<NAME>=true|false in the environment. The script
# always runs every check (regardless of failures) and prints a summary
# at the end. The exit code is non-zero only if an enforced check failed.
set -uo pipefail

# Load defaults from tools/enforcement.config. Values already set in the
# environment win, so a developer can run e.g.
#   ENFORCE_AUTOLINT=true bash tools/run_checks.sh
# without editing the config file.
CONFIG_FILE="$(dirname "$0")/enforcement.config"
if [ -f "$CONFIG_FILE" ]; then
    while IFS='=' read -r key value; do
        case "$key" in ''|\#*) continue;; esac
        key="${key// /}"
        if [ -z "${!key:-}" ]; then
            export "$key=$value"
        fi
    done < "$CONFIG_FILE"
fi

PASSED=()
ADVISORY_FAILED=()
ENFORCED_FAILED=()

# Print colours when stdout is a TTY.
if [ -t 1 ]; then
    GREEN=$'\033[32m'
    YELLOW=$'\033[33m'
    RED=$'\033[31m'
    BOLD=$'\033[1m'
    RESET=$'\033[0m'
else
    GREEN=""; YELLOW=""; RED=""; BOLD=""; RESET=""
fi

run_check() {
    local var_name="$1"   # e.g. RUFF, MYPY, AUTOLINT
    local label="$2"      # human-readable name
    shift 2
    local enforce
    eval "enforce=\${ENFORCE_${var_name}}"

    echo "${BOLD}─── ${label} ───${RESET}"
    if "$@"; then
        echo "${GREEN}✓ ${label} passed${RESET}"
        PASSED+=("$label")
    else
        if [ "$enforce" = "true" ]; then
            echo "${RED}✗ ${label} failed [ENFORCED — fails the build]${RESET}"
            ENFORCED_FAILED+=("$label")
        else
            echo "${YELLOW}⚠ ${label} failed [ENFORCE_${var_name}=${enforce} → not enforced]${RESET}"
            ADVISORY_FAILED+=("$label")
        fi
    fi
    echo
}

run_check RUFF              "Ruff format"      uv run ruff format --check
run_check RUFF              "Ruff lint"        uv run ruff check
run_check MYPY              "Mypy"             uv run mypy src tests
run_check TESTS             "Pytest"           uv run pytest -q
run_check UV_LOCK           "uv lock check"    bash -c '
    before=$(sha256sum uv.lock 2>/dev/null | cut -d" " -f1)
    uv lock >/dev/null 2>&1
    after=$(sha256sum uv.lock 2>/dev/null | cut -d" " -f1)
    if [ "$before" != "$after" ]; then
        echo "uv.lock is out of sync with pyproject.toml; running uv lock would change it."
        exit 1
    fi
'
run_check POSIX_CHECK       "POSIX code check" bash -c 'uv run python tools/check_posix_code.py $(git ls-files "*.py")'
run_check UNLISTED_EVALS    "Unlisted evals"   uv run python tools/check_unlisted_evals.py
run_check GENERATED_DOCS    "Generated READMEs up to date" bash -c '
    uv run python tools/generate_readmes.py --create-missing-readmes >/dev/null 2>&1
    if [ -n "$(git status --porcelain -- "**/README.md" 2>/dev/null)" ]; then
        echo "Generated README sections changed; commit the regenerated files."
        git --no-pager diff -- "**/README.md" | head -40
        exit 1
    fi
'
run_check MARKDOWN_LINT     "Markdown lint"    uv run pre-commit run markdownlint-fix --all-files
run_check LARGE_FILES       "Large-file scan"  bash -c '
    large=$(bash tools/list_large_files.sh 10 2>/dev/null || true)
    if [ -n "$large" ]; then
        echo "Files larger than 10MB found:"
        echo "$large"
        exit 1
    fi
'
run_check AUTOLINT          "Autolint"         uv run python tools/run_autolint.py --all-evals

echo "${BOLD}════════════════════ Summary ════════════════════${RESET}"
echo "Passed:                          ${#PASSED[@]}"
echo "Advisory failures (not enforced): ${#ADVISORY_FAILED[@]}"
echo "Enforced failures:               ${#ENFORCED_FAILED[@]}"

if [ ${#ADVISORY_FAILED[@]} -gt 0 ]; then
    echo
    echo "${YELLOW}Advisory failures (informational only):${RESET}"
    for name in "${ADVISORY_FAILED[@]}"; do
        echo "  ⚠ $name"
    done
    echo
    echo "Set ENFORCE_<NAME>=true to make any of these block the build."
fi

if [ ${#ENFORCED_FAILED[@]} -gt 0 ]; then
    echo
    echo "${RED}Enforced failures (build will fail):${RESET}"
    for name in "${ENFORCED_FAILED[@]}"; do
        echo "  ✗ $name"
    done
    echo
    echo "Set ENFORCE_<NAME>=false to make any of these advisory."
    exit 1
fi

exit 0
