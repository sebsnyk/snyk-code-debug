import os

from ..error_type import ErrorType

# "Snyk Code automatically excludes the following files from analysis: On the
# Web UI - files that are larger than 1MB. On the CLI and IDE - files that are
# larger than 1MB."
# https://docs.snyk.io/supported-languages/technical-specifications-and-guidance
#
# 1MB is written without saying which of the two conventions it means, so take
# the larger reading of 1 MiB. Under the smaller one, every file between
# 1,000,000 and 1,048,576 bytes would be reported as excluded when Snyk in fact
# analyses it. A file wrongly named as a problem costs the user more than the
# scan the check saves.
MAX_FILE_SIZE_BYTES = 1024 * 1024

# "Minified JS files with 3 or fewer lines."
# Same source. Only the line count is observable — nothing in the documentation
# defines "minified", and every heuristic for it (long lines, no spaces after
# commas, a .min. infix) misses real minifiers or catches hand-written code. So
# this reports on the stated line count alone, for JavaScript files, and says so
# in the output. A three-line hand-written file is unusual enough that flagging
# it is worth more than staying quiet about a minified bundle that Snyk skips.
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
