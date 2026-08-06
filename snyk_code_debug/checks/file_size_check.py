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


class FileSizeCheck:
    def __init__(self, file: str):
        self.file = file

    def check(self):
        if os.path.getsize(self.file) > MAX_FILE_SIZE_BYTES:
            return ErrorType.EXCEEDS_SIZE_LIMIT

        return None
