# Working in this repository

## Bump the version in every pull request

`setup.py` carries the version. Raise it in the same PR as the change, never as a
follow-up — the tool is installed straight from the repository with pipx, so the
version is the only thing telling a user which build they are on.

- **Patch** (`0.1.1` → `0.1.2`) — bug fix, documentation, internal refactor.
- **Minor** (`0.1.2` → `0.2.0`) — a new check, a new flag, changed output.
- **Major** — a flag or exit code that existing callers relied on is gone.

Two PRs open at once will both touch that line and the second will conflict. The
conflict is one line and the resolution is always "take the higher number, raise
it again if both were minor".

## This is a public repository

No internal repository names, ticket keys, customer names, hostnames or internal
tooling names — not in code, comments, commit messages, test fixtures or PR
descriptions. Benchmarks and examples use public projects.

## Pull request descriptions

**Problem / Solution / Notes** headings. Keep only what cannot be read off the
diff: why this approach over the obvious alternative, and non-obvious traps.

Cut file-by-file lists, environment excuses, and sign-off filler like "38 tests,
green" or "all tests pass" — CI reports that. Describing what a test *pins* is
useful when it is not obvious; a count never is.

## Tests

Stdlib `unittest` only. `install_requires` is empty and should stay that way, so
a contributor can run the suite against a bare checkout:

```
python3 -m unittest discover -s tests -v
```

Anything that shells out to the Snyk CLI must be injectable, so the suite runs
without the CLI and without network. Cover boundaries exactly — at the limit,
one either side — and use sparse files rather than writing large ones.

## Checks are conservative by default

This tool tells someone which of their files are a problem. A false alarm costs
them more than a wasted scan, so when a documented limit cannot be tested exactly,
either report the observable part and name it as such, or leave it out and record
why in the README.
