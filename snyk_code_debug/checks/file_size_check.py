import os

from ..error_type import ErrorType

# "Snyk Code automatically excludes the following files from analysis: On the
# Web UI - files that are larger than 1MB. On the CLI and IDE - files that are
# larger than 1MB."
# https://docs.snyk.io/supported-languages/technical-specifications-and-guidance
#
# 1MB read as 1 MiB, the larger of the two conventions: under the smaller one
# every file between 1,000,000 and 1,048,576 bytes is reported as excluded when
# Snyk in fact analyses it.
MAX_FILE_SIZE_BYTES = 1024 * 1024

# "Minified JS files with 3 or fewer lines." Nothing defines "minified", so the
# line count alone is reported and the output says so.
MAX_MINIFIED_JS_LINES = 3

JS_EXTENSIONS = ('.js', '.jsx', '.mjs', '.cjs', '.es', '.es6')


def _line_count(path):
    """Newline-delimited lines, counted without holding the file in memory."""
    lines = 0
    with open(path, 'rb') as handle:
        for _ in handle:
            lines += 1
    return lines


class FileSizeCheck:
    def __init__(self, file: str):
        self.file = file

    def check(self):
        if os.path.getsize(self.file) > MAX_FILE_SIZE_BYTES:
            return ErrorType.EXCEEDS_SIZE_LIMIT

        if self.file.lower().endswith(JS_EXTENSIONS):
            # An empty file has no lines to minify and is excluded for a
            # different reason; leave it to the scan rather than mislabel it.
            if 0 < _line_count(self.file) <= MAX_MINIFIED_JS_LINES:
                return ErrorType.LIKELY_MINIFIED

        return None
