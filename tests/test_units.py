"""Unit tests for the pieces that do not shell out.

Stdlib `unittest` only, so `install_requires` stays empty and the suite runs
with `python -m unittest discover` against a bare checkout.
"""
import argparse
import os
import tempfile
import unittest

from snyk_code_debug.error_type import ErrorType
from snyk_code_debug.checks.unicode_check import UnicodeCheck
from snyk_code_debug.gitignore import glob_respecting_gitignore, is_ignored, read_gitignore
from snyk_code_debug.utils.ranged_type import ranged_type


class TestRangedType(unittest.TestCase):

    def setUp(self):
        self.checker = ranged_type(int, 1, 20)

    def test_accepts_value_in_range(self):
        self.assertEqual(self.checker('10'), 10)

    def test_bounds_are_inclusive(self):
        self.assertEqual(self.checker('1'), 1)
        self.assertEqual(self.checker('20'), 20)

    def test_rejects_out_of_range(self):
        for value in ('0', '21'):
            with self.assertRaises(argparse.ArgumentTypeError):
                self.checker(value)

    def test_rejects_non_numeric(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            self.checker('ten')


class TestUnicodeCheck(unittest.TestCase):

    def _write(self, data: bytes) -> str:
        handle = tempfile.NamedTemporaryFile(delete=False, suffix='.cpp')
        handle.write(data)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_utf8_file_passes(self):
        path = self._write('int main() { return 0; }\n'.encode('utf-8'))
        self.assertIsNone(UnicodeCheck(path).check())

    def test_non_utf8_file_is_flagged(self):
        # 0xFF 0xFE is a UTF-16 BOM and is not decodable as UTF-8.
        path = self._write(b'\xff\xfe\x00i\x00n\x00t')
        self.assertEqual(UnicodeCheck(path).check(), ErrorType.NON_UTF8_ENCODING)

    def test_empty_file_passes(self):
        self.assertIsNone(UnicodeCheck(self._write(b'')).check())


class TestGitignore(unittest.TestCase):
    """read_gitignore appends a trailing slash to every entry, so patterns are
    matched as directory prefixes. That is what makes `build` exclude
    `build/x.cpp` without also excluding a file literally named `build`.
    """

    def _gitignore(self, contents: str) -> str:
        handle = tempfile.NamedTemporaryFile('w', delete=False, suffix='.gitignore')
        handle.write(contents)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_comments_and_blank_lines_are_skipped(self):
        path = self._gitignore('# a comment\n\nbuild\n')
        self.assertEqual(read_gitignore(path), ['build/'])

    def test_trailing_slash_is_not_doubled(self):
        path = self._gitignore('vendor/\n')
        self.assertEqual(read_gitignore(path), ['vendor/'])

    def test_missing_file_yields_no_patterns(self):
        self.assertEqual(read_gitignore('/nonexistent/.gitignore'), [])

    def test_is_ignored_matches_directory_prefix(self):
        self.assertTrue(is_ignored('build/main.cpp', ['build/']))
        self.assertFalse(is_ignored('src/main.cpp', ['build/']))

    def test_is_ignored_does_not_match_similar_prefix(self):
        # `buildings/` shares a prefix with `build` but is a different directory.
        self.assertFalse(is_ignored('buildings/main.cpp', ['build/']))


class TestGlobRespectingGitignore(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.getcwd()
        self.addCleanup(os.chdir, self.cwd)
        os.chdir(self.tmp.name)

        os.makedirs('src')
        os.makedirs('build')
        for path in ('src/a.cpp', 'build/b.cpp', 'src/UPPER.CPP'):
            with open(path, 'w') as handle:
                handle.write('int main() { return 0; }\n')

    def _run(self, gitignore=None):
        if gitignore is not None:
            with open('.gitignore', 'w') as handle:
                handle.write(gitignore)
        found = glob_respecting_gitignore(
            '**/*.cpp', gitignore_path='./.gitignore', recursive=True)
        return sorted(found)

    def test_finds_files_recursively(self):
        self.assertIn(os.path.join('src', 'a.cpp'), self._run())

    def test_extension_match_is_case_insensitive(self):
        # The glob pattern is expanded per-character into [cC][pP][pP].
        self.assertIn(os.path.join('src', 'UPPER.CPP'), self._run())

    def test_gitignored_directory_is_excluded(self):
        found = self._run(gitignore='build\n')
        self.assertNotIn(os.path.join('build', 'b.cpp'), found)
        self.assertIn(os.path.join('src', 'a.cpp'), found)


if __name__ == '__main__':
    unittest.main()
