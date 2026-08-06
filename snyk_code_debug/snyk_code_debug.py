import argparse
import tempfile
import shutil
import traceback
import concurrent
import concurrent.futures
import os.path
import sys

from .bisect import (
    BISECT_MIN_FILES, Bisector, ScanBudgetExceeded, default_max_depth)
from .gitignore import glob_respecting_gitignore
from .progress import update_progress_bar
from .error_type import ErrorType
from .checks.snyk_code_check import SnykCodeCheck, failed_parsing
from .checks.unicode_check import UnicodeCheck
from .checks.file_size_check import FileSizeCheck
from .utils.ranged_type import ranged_type

SUPPORTED_EXTENSIONS = ['apex','aspx','c','cc','cjs','cls','cpp','cs','ejs','erb','es','es6','go','groovy','h','haml','hpp','htm','html','hxx','java','js','jspx','jsx','jsp','kt','m','mjs','mm','php','py','rb','rhtml','rs','scala','slim','swift','ts','tsx','trigger','vb','vue','xml']

def main_function():
    parser = argparse.ArgumentParser(description='snyk-code-debug: Finds files that failed analysis')

    parser.add_argument('--extension', type=str, required=True, choices=SUPPORTED_EXTENSIONS, help='The file extension to search for')
    parser.add_argument('--concurrency','-c', type=ranged_type(int, 1, 20), default=10, help='Concurrency')
    parser.add_argument('--max-errors', type=ranged_type(int, 1, 100), default=None, help='Max errors')
    parser.add_argument('--evidence-collection', type=str, default=None, help='Copies unanalyzed files to this folder')
    parser.add_argument('--strategy', choices=['bisect', 'linear'], default='bisect',
                        help='bisect (default) scans subsets and splits only the dirty half; linear scans every file')
    parser.add_argument('--max-scans', type=int, default=None,
                        help='Abort bisect after this many scans and report what was found so far')
    parser.add_argument('--max-depth', type=int, default=None,
                        help='After this many splits, scan the remaining subset file by file. Bounds the cost when failures are dense. Defaults to a value derived from the file count')

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

    # Every file shells out to the Snyk CLI. Without it each worker raises
    # FileNotFoundError, the executor prints a traceback per file, and the run
    # still exits 0 reporting nothing wrong — the worst outcome for a tool whose
    # job is to tell you which files failed. Fail once, up front, instead. Checked
    # after file discovery so a run with nothing to scan does not need the CLI.
    if shutil.which('snyk') is None:
        print('The Snyk CLI is not on PATH. Install it from https://docs.snyk.io/snyk-cli/install-or-update-the-snyk-cli and run `snyk auth`.')
        sys.exit(1)

    files_processed = 0

    failed_files = {enum: [] for enum in ErrorType}

    # These checks read the file locally, so they cost nothing and their
    # results are the same under either strategy. Doing them first also keeps
    # the files they flag out of the scanned set entirely. Size goes before
    # encoding: a stat is cheaper than the unicode check, which reads the whole
    # file into memory.
    for file in list(results):
        for check in (FileSizeCheck, UnicodeCheck):
            error = check(file).check()
            if error is not None:
                failed_files[error].append(file)
                results.remove(file)
                break

    # Below the threshold the grouped scans cannot pay for themselves. Switch
    # silently — the strategy is an implementation detail, not something a user
    # running this against their own codebase needs narrated.
    if args.strategy == 'bisect' and len(results) < BISECT_MIN_FILES:
        args.strategy = 'linear'

    if args.strategy == 'bisect':
        def report(scan_number, subset_size):
            print(f'\rScan {scan_number}: {subset_size} file(s)', end='')

        depth = args.max_depth
        if depth is None:
            depth = default_max_depth(len(results))

        bisector = Bisector(failed_parsing, max_scans=args.max_scans,
                            max_depth=depth, on_scan=report)
        try:
            failed_files[ErrorType.ANALYSIS_ERROR] = bisector.find(results)
        except ScanBudgetExceeded as exceeded:
            failed_files[ErrorType.ANALYSIS_ERROR] = exceeded.found or []
            print(f'\nStopped after {exceeded.scans} scans (--max-scans). Results are partial.')
        print(f'\rCompleted in {bisector.scans} scan(s) for {len(results)} file(s).')
        return _report(args, failed_files)

    total_files = len(results)
    if total_files == 0:
        return _report(args, failed_files)

    update_progress_bar(files_processed, total_files)

    def process_file(file):
        # Undecodable files were filtered out before this point.
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

    return _report(args, failed_files)


def _report(args, failed_files):
    """Print the outcome and exit. Shared by both strategies."""
    if not any(failed_files.values()):
        print('All files parsed successfully.')
        sys.exit(0)

    errors = failed_files[ErrorType.NON_UTF8_ENCODING]
    if len(errors) > 0:
        print('Files in non-UTF-8 encoding detected:')
        for file in errors:
            print(file)

    errors = failed_files[ErrorType.EXCEEDS_SIZE_LIMIT]
    if len(errors) > 0:
        print('Files above the 1MB Snyk Code size limit detected, these are excluded from analysis:')
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

    # Non-zero so the tool is usable as a CI gate, not just interactively.
    sys.exit(1)

if __name__ == '__main__':
    main_function()
