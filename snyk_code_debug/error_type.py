from enum import Enum

class ErrorType(Enum):
    NON_UTF8_ENCODING = 1
    ANALYSIS_ERROR = 2
    EXCEEDS_SIZE_LIMIT = 3
    LIKELY_MINIFIED = 4
