import glob
import os.path
import fnmatch

def read_gitignore(gitignore_path):
    patterns = []
    if os.path.isfile(gitignore_path):
        with open(gitignore_path, 'r') as file:
            for line in file:
                stripped_line = line.strip()
                if stripped_line and not stripped_line.startswith('#'):
                    if not stripped_line.endswith('/'):
                        stripped_line += '/'
                    patterns.append(stripped_line)
    return patterns

def is_ignored(path, ignore_patterns):
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(path, pattern) or path.startswith(pattern):
            return True
    return False

def glob_respecting_gitignore(pattern, gitignore_path='/.gitignore', recursive=True):
    ignore_patterns = read_gitignore(gitignore_path)
    all_files = glob.glob(pattern, recursive=recursive)
    return [file for file in all_files if not is_ignored(file, ignore_patterns)]
