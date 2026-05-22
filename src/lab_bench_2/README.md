# LABBench2

LABBench2 evaluates language models and research agents on life-science tasks spanning literature reasoning, database access, figures, tables, protocols, source quality, sequence analysis, cloning, patents, and clinical trials.

<!-- Contributors: Automatically Generated -->
Contributed by [@iphan](https://github.com/iphan)
<!-- /Contributors: Automatically Generated -->

<!-- Usage: Automatically Generated -->
## Usage

First, install dependencies:

```bash
uv sync
```

Then run evaluations:

```bash
uv run inspect eval lab_bench_2/lab_bench_2 --model openai/gpt-5-nano
```

You can also import tasks as Python objects:

```python
from inspect_ai import eval
from lab_bench_2 import lab_bench_2
eval(lab_bench_2)
```

After running evaluations, view logs with:

```bash
uv run inspect view
```

If you don't want to specify `--model` each time, create a `.env` file:

```bash
INSPECT_EVAL_MODEL=anthropic/claude-opus-4-1-20250805
ANTHROPIC_API_KEY=<anthropic-api-key>
```
<!-- /Usage: Automatically Generated -->

<!-- Options: Automatically Generated -->
## Options

You can control a variety of options from the command line. For example:

```bash
uv run inspect eval lab_bench_2/lab_bench_2 --limit 10
uv run inspect eval lab_bench_2/lab_bench_2 --max-connections 10
uv run inspect eval lab_bench_2/lab_bench_2 --temperature 0.5
```

See `uv run inspect eval --help` for all available options.
<!-- /Options: Automatically Generated -->

<!-- Parameters: Automatically Generated -->
## Parameters

### `lab_bench_2`

- `tag` (str): Which LAB-Bench 2 subset to run. Phase 1 supports only "litqa3". (default: `'litqa3'`)
- `mode` (Mode): How a question's data files are delivered to the model. A no-op for tags without files (such as litqa3). Options: ``file``: Files uploaded via API. Smart routing: PDFs/images → context; other files → provider-side filesystem/container when code execution is enabled, else context., ``inject``: Text file contents concatenated into the prompt as text., ``retrieve``: Only file names/stems are given; prompt instructs the agent to retrieve the necessary sequences or data from a source of its choosing. File contents are withheld. (default: `'inject'`)
- `solver` (Solver | None): The solver to run. Defaults to ``bare()`` (the benchmark's "bare" configuration: a plain single-turn ``generate()``) when not provided. Pass any Inspect solver to override, e.g. ``-T solver=bare`` on the CLI. (default: `None`)
<!-- /Parameters: Automatically Generated -->

## Dataset

This eval uses the public `EdisonScientific/labbench2` dataset on Hugging Face, pinned to a specific commit for reproducibility.

## Scoring

Answers are graded by a semantic LLM judge. The judge compares the model's
answer to the reference, accepting semantically or numerically equivalent
answers, and returns one of `correct` / `incorrect` / `unsure`; a `correct`
verdict scores 1.0 and everything else (including unparseable or empty
judgements) scores 0.0. Reported metrics are `accuracy` and `stderr`.

The judge model is selected via the `grader` model role and defaults to
`anthropic/claude-sonnet-4-5` at temperature 0. Override it on the command line,
for example:

```bash
uv run inspect eval lab_bench_2/lab_bench_2 \
  --model openai/gpt-5-nano \
  --model-role grader=anthropic/claude-sonnet-4-5
```

## Evaluation Report

TODO: A brief summary of results for your evaluation implementation compared against a standard set of existing results.

## Changelog
