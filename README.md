# Debugging Snyk Code scan results

**Warning:** This tool will perform a inefficient file analysis, one by one. This will consume snyk tests. Use with caution.

## Purpose

This tool helps to identify specific files that have failed parsing by Snyk Code.

Additionally, a small set of pre-flight checks is included and affected files are listed. The list of checks currently includes:
- **Unicode check**, files not encoded in UTF-8 or compatible (e.g. CP1252) will be printed out separately. 

For a whole set of restrictions around Snyk Code's supported files, please see the [documentation](https://docs.snyk.io/scan-using-snyk/supported-languages-and-frameworks/introduction-to-snyk-supported-languages-and-frameworks#file-size-limit-for-snyk-code-analysis).

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