# Debugging Snyk Code scan results

**Warning:** This tool will perform a inefficient file analysis, one by one. This will consume snyk tests. Use with caution.

## Purpose

This tool helps to identify specific files that have failed parsing by Snyk Code.

Pre-flight checks run against the file on disk before any scan, so a flagged file is reported with a reason and costs no Snyk test:

- **Unicode** — not UTF-8 or compatible.
- **File size** — larger than 1 MiB.
- **Short JavaScript** — JavaScript of three lines or fewer.

For a whole set of restrictions around Snyk Code's supported files, please see the [technical specifications and guidance](https://docs.snyk.io/supported-languages/technical-specifications-and-guidance).

## Requirements

The [Snyk CLI](https://docs.snyk.io/snyk-cli/install-or-update-the-snyk-cli) must be on your `PATH` and authenticated (`snyk auth`) — this tool drives it once per file.

## Installation

This tool is not published to PyPI. Install it straight from the repository with [pipx](https://pipx.pypa.io/), which puts the command on your `PATH` in its own isolated environment:

```
pipx install git+https://github.com/sebsnyk/snyk-code-debug.git
```

To upgrade later:

```
pipx upgrade snyk-code-debug
```

`pip install git+…` also works, but on any Python installed via Homebrew or a system package manager it will refuse with `externally-managed-environment` ([PEP 668](https://peps.python.org/pep-0668/)) unless you are inside a virtualenv. pipx sidesteps that.

## Usage

The script will collect all files specified by the `extension` command line argument.

```
% snyk-code-debug --extension cpp
```

A list of files will be returned that have failed parsing:

```
% snyk-code-debug --extension cpp
Determining file list.
Progress: [####################] 100% Completed
Some files have failed analysis:
invalid-file.cpp
```

## Exit codes

| Code | Meaning |
| ---- | ------- |
| `0`  | Every file parsed successfully |
| `1`  | Files failed analysis or were flagged by a pre-flight check, or the Snyk CLI is missing / the evidence directory is invalid |

The non-zero exit on failures makes the tool usable as a CI gate.

## Development

Install an editable copy into a virtualenv:

```
python3 -m venv .venv && .venv/bin/pip install -e .
```

Or run the checked-out source directly through pipx:

```
pipx install --editable .
```

### Tests

Stdlib `unittest`, no test dependencies:

```
python3 -m unittest discover -s tests -v
```