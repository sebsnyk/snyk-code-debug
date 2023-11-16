# Debugging Snyk Code scan results

**Warning:** This tool will perform a inefficient file analysis, one by one. This will consume snyk tests. Use with caution.

## Installation

This tool is not available in public `pip`, therefore please install it using:

```
pip install git+https://github.com/sebsnyk/snyk-code-debug.git
```

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