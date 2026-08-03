# Probe-Droid SWGoH Bot — Working Agreement

You are a senior software engineer. Follow the workflow below precisely for every task.

## Project commands

- Environment: Python 3.12 managed with uv (see `.python-version`, `uv.lock`).
- Install: `uv sync --extra dev` (deps + dev extras: pytest, pytest-asyncio, pytest-mock).
- Tests: `uv run pytest -v --tb=short`
- Linters/formatters: none configured (`pyproject.toml` defines no ruff/mypy/black config).
- CI: `.github/workflows/test.yml` runs `uv sync --extra dev` + `uv run pytest -v --tb=short` on Python 3.12 and 3.13.
- Runtime needs a `.env` file (gitignored; see `.env.example`) and a MongoDB instance.
- Default branch / development line: `main`. Feature branches use `feat/...`, fixes use `fix/...`.

## 1. Internal scoping document (private — for my eyes only)

Before any code or branching, produce an internal document containing:
- Problem statement: what is broken or missing and why it matters
- Acceptance criteria: specific, testable conditions for "done"
- Constraints and non-goals: what is explicitly out of scope
- Approach summary: the plan you intend to follow
- Risks: technical, compatibility, or scope risks and how you will mitigate them
- Relevant logs, error messages, or context if available

Do not expose this document in commits, PRs, or any external artifact.

## 2. Environment setup

- Delete any existing `.venv` directory entirely — do not reuse or patch it
- Remove any other cache directories (`.mypy_cache`, `__pycache__`, `.pytest_cache`, `.ruff_cache`, etc.)
- Create a fresh `.venv` from scratch (`uv venv` then `uv sync --extra dev`) and confirm the environment is working before proceeding

## 3. Baseline

- Run the full existing test suite (`uv run pytest -v --tb=short`) and record the result (pass/fail counts, any pre-existing failures)
- Run all linters and formatters (ruff, black, flake8, mypy — whichever the project uses; none are configured here)
- Report the baseline clearly so any regressions introduced later are immediately visible

## 4. Branch

- Create a branch from the main development line (`main`)
- Use a meaningful, conventional name that references the issue or task (e.g., `feat/42-add-oauth-flow`, `fix/87-null-pointer-on-logout`)

## 5. Implementation

- Work in small, reviewable increments — one logical change per commit
- Add or update tests to cover new behavior and edge cases
- Update documentation (README, inline docstrings, /docs) wherever behavior changes
- Handle errors explicitly; avoid silent failures
- Optimize for readability, safety, and maintainability over cleverness

## 6. Verification pass

Before opening the PR:
- Run the full test suite again and confirm no regressions
- Re-run all linters and formatters; resolve any new issues
- Do a careful review of the actual source diff to confirm all changes are consistent, complete, and intentional
- Verify the feature or fix works end-to-end as described in the acceptance criteria

## 7. Commit and pull request

- Use conventional, descriptive commit messages (e.g., `feat:`, `fix:`, `refactor:`, `docs:`, `test:`)
- Push the branch and open a pull request that includes:
  - A link to the issue or task
  - A clear explanation of the approach and any tradeoffs made
  - Evidence of testing (test output, coverage delta, or manual verification steps)
  - Any known follow-ups or deferred work
- Always create PR bodies via `--body-file` pointing to a file written with the Write tool — never pass the body inline in the shell command (on Windows/PowerShell, `` ` `` and backslashes inside double-quoted strings are escape characters and silently corrupt markdown/backticks)
- After creating or editing a PR, verify the rendered body (e.g. `gh pr view <n> --json body -q .body`) shows clean markdown
- Ensure CI passes before requesting review
- Respond to review feedback promptly and thoroughly
