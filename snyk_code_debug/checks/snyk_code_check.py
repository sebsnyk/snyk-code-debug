import subprocess

from ..snyk_code_debug import ErrorType

COMMAND=['snyk', 'code', 'test', '--debug']

def _scan(folder: str) -> str:
    """Run the Snyk CLI over a folder and return its combined output.

    `snyk code test` exits 1 when it finds issues, so a non-zero status is
    normal rather than a failure. The output still has to be read in that case:
    it carries the FAILED_PARSING lines. Discarding it hides a parse error in
    any folder that also contains a real finding — harmless when scanning one
    file at a time, wrong as soon as a folder holds more than one.
    """
    try:
        completed = subprocess.run(
            COMMAND, cwd=folder, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        # main_function pre-flights the CLI, so reaching here means it went
        # missing mid-run. Swallowing it would report every remaining file
        # as clean.
        raise
    return completed.stdout.decode(errors='replace')


def failed_parsing(folder: str) -> bool:
    """True if any file in the folder failed to parse."""
    return any('FAILED_PARSING' in line for line in _scan(folder).split('\n'))


class SnykCodeCheck:
    def __init__(self, tmpfolder: str):
        self.tmpfolder = tmpfolder

    def check(self):
        if failed_parsing(self.tmpfolder):
            return ErrorType.ANALYSIS_ERROR

        return None
