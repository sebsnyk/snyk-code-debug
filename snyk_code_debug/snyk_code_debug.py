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
from .utils.ranged_type import ranged_type

SUPPORTED_EXTENSIONS = ['apex','aspx','c','cc','cjs','cls','cpp','cs','ejs','erb','es','es6','go','groovy','h','haml','hpp','htm','html','hxx','java','js','jspx','jsx','jsp','kt','m','mjs','mm','php','py','rb','rhtml','rs','scala','slim','swift','ts','tsx','trigger','vb','vue','xml']

def main_function():
    parser = argparse.ArgumentParser(description='snyk-code-debug: Finds files that failed analysis')

    parser.add_argument('--extension', type=str, required=True, choices=SUPPORTED_EXTENSIONS, help='The file extension to search for')
    parser.add_argument('--concurrency','-c', type=ranged_type(int, 1, 20), default=10, help='Concurrency')
    parser.add_argument('--max-errors', type=ranged_type(int, 1, 100), default=None, help='Max errors')
    parser.add_argument('--evidence-collection', type=str, default=None, help='Copies unanalyzed files to this folder')

    args = parser.parse_args()

    print('Determining file list.')

    if args.evidence_collection is not None:
        if not os.path.isdir(args.evidence_collection):
            print('Evidence collection directory does not exist or is invalid')
            sys.exit(1)

    results = glob_respecting_gitignore('**/*.{}'.format(args.extension), gitignore_path='./.gitignore', recursive=True)
    total_files = len(results)

    if total_files == 0:
        print('No relevant files detected.')
        sys.exit(0)

    files_processed = 0

    failed_files = {enum: [] for enum in ErrorType}

    update_progress_bar(files_processed, total_files)

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

            total_failures = sum(len(files) for files in failed_files.values())
            if args.max_errors is not None and total_failures >= args.max_errors:
                executor.shutdown(wait=True)
                break

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
            if args.evidence_collection is not None:
                for file in errors:
                    # copy file to evidence collection folder
                    shutil.copy(file, args.evidence_collection)
                print('Evidence collection completed, stored in folder: {}'.format(args.evidence_collection))
        print('All files parsed successfully.')

if __name__ == '__main__':
    main_function()
