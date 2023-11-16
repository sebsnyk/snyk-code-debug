import argparse
import tempfile
import shutil
import subprocess
import concurrent
import concurrent.futures
import os.path
import sys

from .gitignore import glob_respecting_gitignore
from .progress import update_progress_bar
COMMAND=['snyk', 'code', 'test', '--debug']
SUPPORTED_EXTENSIONS = ['apex','ASPX','c','cc','cjs','cls','cpp','CS','ejs','erb','es','es6','go','h','haml','hpp','htm','html','hxx','java','js','jspx','jsx','jsp','kt','mjs','php','py','rb','rhtml','scala','slim','swift','ts','tsx','trigger','vb','vue','xml']

def main_function():
    parser = argparse.ArgumentParser(description='snyk-code-debug: Finds files that failed analysis')

    # Add the arguments
    parser.add_argument('--extension', type=str, required=True, choices=SUPPORTED_EXTENSIONS, help='The file extension to search for')
    parser.add_argument('--concurrency', type=int, default=10, choices=range(1, 20), help='Concurrency')

    # Execute the parse_args() method
    args = parser.parse_args()

    print('Determining file list.')

    results = glob_respecting_gitignore('**/*.{}'.format(args.extension), gitignore_path='./.gitignore', recursive=True)
    total_files = len(results)
    
    if total_files == 0:
        print('No relevant files detected.')
        sys.exit(0)
    
    files_processed = 0

    failed_files = []
    def process_file(file):
        with tempfile.TemporaryDirectory() as tmpdirname:
            basename = os.path.basename(file)
            shutil.copyfile(file, f'{tmpdirname}/{basename}')
            try:
                output = subprocess.check_output(COMMAND, cwd=tmpdirname, stderr=subprocess.STDOUT).decode()

                for line in output.split('\n'):
                    if 'FAILED_PARSING' in line:
                        failed_files.append(file)
                        break
            except subprocess.CalledProcessError as e:
                pass
                

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = [executor.submit(process_file, file) for file in results]

        for future in concurrent.futures.as_completed(futures):
            files_processed += 1
            update_progress_bar(files_processed, total_files)

            if future.exception():
                print(f"Exception occurred: {future.exception()}")

        print()

    if len(failed_files) > 0:
        print('Some files have failed analysis:')
        for file in failed_files:
            print(file)
    else:
        print('All files parsed successfully.')

if __name__ == '__main__':
    main_function()