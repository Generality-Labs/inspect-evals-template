# GPQA

[GPQA](https://arxiv.org/pdf/2311.12022) is a graduate-level multiple-choice
benchmark spanning physics, chemistry, and biology. This implementation
evaluates the GPQA-Diamond subset (198 questions).

Adapted from the
[inspect_evals implementation](https://github.com/UKGovernmentBEIS/inspect_evals/tree/main/src/inspect_evals/gpqa)
and [simple-evals](https://github.com/openai/simple-evals/blob/main/gpqa_eval.py).

<!-- Contributors: Automatically Generated -->
Contributed by [@jjallaire](https://github.com/jjallaire)
<!-- /Contributors: Automatically Generated -->

## Usage

The examples are not registered as a package, so run this one by file path from the repo root:

```bash
uv run inspect eval src/examples/gpqa/gpqa.py --model openai/gpt-5-nano
uv run inspect eval src/examples/gpqa/gpqa.py --model openai/gpt-5-nano --limit 10 --epochs 1
uv run inspect eval src/examples/gpqa/gpqa.py --model openai/gpt-5-nano -T high_level_domain=Biology
```

View the logs with `uv run inspect view`. See `uv run inspect eval --help` for all available options.

<!-- Parameters: Automatically Generated -->
## Parameters

### `gpqa_diamond`

- `cot` (bool): Whether to use chain-of-thought reasoning (default True). (default: `True`)
- `epochs` (int): Number of epochs to run (default 4). (default: `4`)
- `high_level_domain` (str | list[str] | None): Optional high-level domain(s) to filter by. One of "Biology", "Chemistry", or "Physics", or a list of these. If None, all domains are included. (default: `None`)
- `subdomain` (str | list[str] | None): Optional subdomain(s) to filter by (e.g. "Genetics" or "Quantum Mechanics", or a list of these). If None, all subdomains are included. (default: `None`)
<!-- /Parameters: Automatically Generated -->

## Dataset

Example prompt (after processing by Inspect):

> Answer the following multiple choice question. The entire content of your
> response should be of the following format: 'ANSWER: $LETTER' (without
> quotes) where LETTER is one of A,B,C,D.
>
> Two quantum states with energies E1 and E2 have a lifetime of 10^-9 sec
> and 10^-8 sec, respectively. We want to clearly distinguish these two
> energy levels. Which one of the following options could be their energy
> difference so that they can be clearly resolved?
>
> A) 10^-4 eV
> B) 10^-11 eV
> C) 10^-8 eV
> D) 10^-9 eV

## Scoring

Simple accuracy over multiple-choice answers.

## Evaluation Report

Results on the full GPQA-Diamond dataset (198 samples, 1 epoch):

| Model                      | Provider  | Accuracy | Stderr | Time   |
| -------------------------- | --------- | -------- | ------ | ------ |
| gpt-5.1-2025-11-13         | OpenAI    | 0.652    | 0.034  | 2m 6s  |
| claude-sonnet-4-5-20250929 | Anthropic | 0.717    | 0.032  | 4m 49s |
| gemini-3-pro-preview       | Google    | 0.929    | 0.018  | 70m    |

**Notes:**

- Human expert baseline from the paper is 69.7% accuracy.
- GPT 5.1 and Claude completed all 198 samples.
- Gemini 3 Pro completed 197/198 samples after 70 minutes.
- Results generated December 2025 using the inspect_evals implementation.
