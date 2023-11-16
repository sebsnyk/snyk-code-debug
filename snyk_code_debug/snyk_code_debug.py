import argparse
import tempfile
import shutil
import traceback
import concurrent
import concurrent.futures
import os.path
import sys

from .gitignore import glob_respecting_gitignore
from .progress import update_progress_bar
from .error_type import ErrorType
from .checks.snyk_code_check import SnykCodeCheck
from .checks.unicode_check import UnicodeCheck

SUPPORTED_EXTENSIONS = ['apex','aspx','c','cc','cjs','cls','cpp','cs','ejs','erb','es','es6','go','h','haml','hpp','htm','html','hxx','java','js','jspx','jsx','jsp','kt','mjs','php','py','rb','rhtml','scala','slim','swift','ts','tsx','trigger','vb','vue','xml']

def main_function():
    parser = argparse.ArgumentParser(description='snyk-code-debug: Finds files that failed analysis')

    parser.add_argument('--extension', type=str, required=True, choices=SUPPORTED_EXTENSIONS, help='The file extension to search for')
    parser.add_argument('--concurrency', type=int, default=10, choices=range(1, 20), help='Concurrency')

    args = parser.parse_args()

    print('Determining file list.')

    results = glob_respecting_gitignore('**/*.{}'.format(args.extension), gitignore_path='./.gitignore', recursive=True)
    total_files = len(results)
    
    if total_files == 0:
        print('No relevant files detected.')
        sys.exit(0)
    
    files_processed = 0

    failed_files = {enum: [] for enum in ErrorType}

    def process_file(file):
        unicode_check = UnicodeCheck(file).check()
        if unicode_check is not None:
            failed_files[unicode_check].append(file)
            return
        
        with tempfile.TemporaryDirectory() as tmpdirname:
            
            basename = os.path.basename(file)
            shutil.copyfile(file, f'{tmpdirname}/{basename}')
            
            
            code_check = SnykCodeCheck(tmpdirname).check()
            if code_check is not None:
                failed_files[code_check].append(file)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(process_file, file) for file in results]

        for future in concurrent.futures.as_completed(futures):
            files_processed += 1
            update_progress_bar(files_processed, total_files)

            exception = future.exception()
            if exception:
                print("Exception occurred:")
                traceback.print_exception(type(exception), exception, exception.__traceback__)


        print()

    if any(failed_files.values()):
        errors = failed_files[ErrorType.NON_UTF8_ENCODING]
        if len(errors) > 0:
            print('Files in non-UTF-8 encoding detected:')
            for file in errors:
                print(file)
                
        errors = failed_files[ErrorType.ANALYSIS_ERROR]
        if len(errors) > 0:
            print('Analysis errors detected with the following files:')
            for file in errors:
                print(file)
    else:
        print('All files parsed successfully.')

if __name__ == '__main__':
    main_function()