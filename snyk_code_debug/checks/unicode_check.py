from ..snyk_code_debug import ErrorType

class UnicodeCheck:
    def __init__(self, file: str):
        self.file = file
        
    def is_utf8_compatible(self, filename):
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                file.read()
            return True
        except UnicodeDecodeError:
            return False

    def check(self):
        if self.is_utf8_compatible(self.file):
            return None
        
        return ErrorType.NON_UTF8_ENCODING