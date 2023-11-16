import subprocess

from ..snyk_code_debug import ErrorType

COMMAND=['snyk', 'code', 'test', '--debug']

class SnykCodeCheck:
    def __init__(self, tmpfolder: str):
        self.tmpfolder = tmpfolder
    
    def check(self):
        try:
            output = subprocess.check_output(COMMAND, cwd=self.tmpfolder, stderr=subprocess.STDOUT).decode()

            for line in output.split('\n'):
                if 'FAILED_PARSING' in line:
                    return ErrorType.ANALYSIS_ERROR
        except subprocess.CalledProcessError as e:
            pass
        
        return None
