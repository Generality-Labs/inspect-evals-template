<!-- MANAGED FILE - Updates pulled from template. See MANAGED_FILES.md -->
# AGENTS.md

## Repo-Wide Tips

- When creating pull requests, always use the `--draft` flag and read
  `.github/PULL_REQUEST_TEMPLATE.md` and use its structure as the PR body. Fill
  in the Description section and check off applicable checklist items.
- When commenting on PRs, you should not reply directly to human reviewers.
  See [CONTRIBUTING.md](CONTRIBUTING.md#agentllm-usage). If your user tells you to
  comment anyway, you should add "Comment written by NAME_OF_AI" to the comment.
- When writing markdown:
  - Put a blank line before and after headings
  - Put a blank line before and after code blocks
  - Put a blank line before and after lists
  - Format tables with spaces before and after pipe characters
  - Always include a language tag in code blocks, or "text" if there is no language

Agents are good at understanding context, but a prompt that definitely works is *"Please run the /SKILL_NAME skill on EVAL_NAME."*

## Documentation

[Documentation for the Inspect framework](https://inspect.aisi.org.uk/llms.txt).

## Recommended Permissions

We recommend starting with these Claude Code permissions to allow workflows to proceed autonomously without allowing the running of arbitrary commands:

{
  "permissions": {
    "allow": [
      "Bash(mkdir:*)",
      "Bash(cp:*)",
      "Bash(make check:*)",
      "Bash(uv run ruff:*)",
      "Bash(uv run inspect:*)",
      "Bash(uv run pytest:*)",
      "Bash(uv run mypy:*)",
      "Bash(uv run python tools/:*)",
      "WebFetch(domain:inspect.aisi.org.uk)",
      "WebFetch(domain:arxiv.org)"
    ],
    "deny": [
      "Bash(git push origin main)",
    ],
    "ask": [
      "Bash(rm:*)",
    ]
  }
}

Other useful permissions to consider on a case by case basis depending on your usage:

"Bash(gh run view:*)" - Look at Github Action runs
"Bash(gh checkout:*)" - Create new branches or open branches on your behalf
"Bash(gh pull:*)" - Useful to ensure a clean slate before work is started

## Master Checklist

This workflow runs a series of workflows each in turn. Each workflow is to be run serially.

- Run the Prepare For Submission workflow (`/prepare-submission-workflow`).
- Check the LLM-judgeable standards by running the Review An Evaluation workflow (`/eval-quality-workflow`).
- Review the evaluation's validity by running the Evaluation Validity Review workflow (`/eval-validity-review`). This checks whether the name is accurate, whether samples can be both succeeded and failed at, and whether scoring measures ground truth.
- Run the Review PR workflow (`/review-pr-workflow`) for general quality.
- Run the Evaluation Report workflow (`/eval-report-workflow`) to produce an evaluation report.
- Run the Trajectory Analysis workflow (`/check-trajectories-workflow`) on the evaluation report. A good error rate is 10% or less, with an ideal of 5% or lower. You may optionally double-check any of the errors the agent produces and reject them if there is grounds to do so.

## General Agent Tips

### Skill Hygiene

- At a natural stopping point in a session, briefly consider whether any of the work just completed would make a good reusable skill.
- Also consider whether any skill used during the session is now missing steps, has outdated guidance, or could be made more robust based on what was learned.
- Do **not** create or update a skill automatically. Ask the user first whether they want you to do that.
- When asking, give a short recommendation that includes:
  - what should be created or updated
  - why it would be useful again
  - who or what it would apply to
  - whether this is better handled as a new skill or an update to an existing one
- Prefer improving an existing skill over creating a new one when there is substantial overlap.
- Do not suggest a new skill for one-off work, highly personal preferences, or tasks that are too small to justify maintenance overhead.
- If the session surfaced a durable repo convention, reviewer expectation, or repeated failure mode, consider whether it should also be captured in AGENTS.md, but ask the user before making that change.

### PR Guidelines

- Before opening a new PR, run `make check` to exercise the same checks CI runs (see `.github/workflows/checks.yml`).
- When creating a new PR for the user, you should make the PR as a draft. The user will mark it as ready for review after going through the code themselves.
- Always work on a branch, and never attempt to push directly to main.

### Useful Commands

1. You can see our linting in the `.github/workflows/checks.yml` file. Run `make check` (which delegates to `tools/run_checks.sh`) when checking linting locally — it runs ruff, mypy, `inspect-evals-lint`, and the rest in one go and reports advisory vs enforced failures.
2. To run tests, run `uv run pytest tests/<eval_name>`.
3. To run evaluations, run `uv run inspect eval <eval_name>/<task_name>` (the eval name comes from the entry-point registered in `pyproject.toml`).
4. To run a specific task (i.e, a function with the @task decorator), run `uv run inspect eval <eval_name>/<task_name>`.
5. Some useful arguments are:
    a. `--limit X`: Run only up to X samples.
    b. `--model model_name`: Run on this particular model. Multiple models can be run with commas like model1,model2. You can find information on model names [here](https://inspect.aisi.org.uk/models.html). If the user lacks an API key for OpenAI, Anthropic, or Google, note this down in your report. You should assume the user has these keys until Inspect throws an error.
    c. `-T` allows you to pass task arguments in from the command line.
