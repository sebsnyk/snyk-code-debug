"""Find the files that fail parsing by bisecting the set, not scanning each one.

The linear strategy runs one scan per file: N files, N scans, N consumed tests.
Almost all of that is wasted, because the answer is usually a handful of bad
files in a large tree.

This is the classic group-testing problem. Scan a whole subset at once; a clean
result clears every file in it with a single scan. Only a dirty subset is split
and re-examined. For k bad files among N the cost is roughly k * log2(N/k)
scans instead of N — for 5 bad files in 2000, about 50 scans rather than 2000.

The trade-off is real and worth stating: when almost everything is broken,
bisection costs *more* than linear, up to 2N-1 scans, because every split ends
up dirty on both sides and nothing is ever pruned. `--max-scans` bounds that,
and small subsets stop splitting and go linear where the recursion overhead
outweighs the pruning.

The whole approach leans on Snyk Code caching analysis results, so re-scanning
a file that already appeared in a larger subset is cheap. If that caching is
per-path rather than per-content, moving files into new temporary folders will
miss the cache: the results stay correct, the savings shrink.
"""
import os
import shutil
import tempfile

# Below this size, splitting costs more scans than just testing each file.
LINEAR_THRESHOLD = 3


class ScanBudgetExceeded(Exception):
    def __init__(self, found, scans):
        super().__init__(f'scan budget exhausted after {scans} scans')
        self.found = found
        self.scans = scans


class Bisector:
    """Locates failing files by recursive subset elimination.

    scan_folder -- callable taking a directory path, returning True if anything
        in it failed to parse. Injected so the search can be tested without the
        Snyk CLI.
    """

    def __init__(self, scan_folder, max_scans=None, on_scan=None):
        self.scan_folder = scan_folder
        self.max_scans = max_scans
        self.on_scan = on_scan
        self.scans = 0

    def _scan(self, files):
        """Stage `files` in a flat temporary folder and scan it.

        Basenames can collide across directories, so each file gets an index
        prefix. Two files that differ only by directory would otherwise
        overwrite each other and one of them would never be tested.
        """
        if self.max_scans is not None and self.scans >= self.max_scans:
            raise ScanBudgetExceeded(found=None, scans=self.scans)

        with tempfile.TemporaryDirectory() as folder:
            for index, path in enumerate(files):
                staged = os.path.join(folder, f'{index}_{os.path.basename(path)}')
                shutil.copyfile(path, staged)
            self.scans += 1
            if self.on_scan is not None:
                self.on_scan(self.scans, len(files))
            return self.scan_folder(folder)

    def find(self, files):
        """-> sorted list of files that fail parsing."""
        files = list(files)
        if not files:
            return []
        try:
            return sorted(self._find(files))
        except ScanBudgetExceeded as exceeded:
            exceeded.found = sorted(exceeded.found or [])
            raise

    def _find(self, files):
        if not self._scan(files):
            return []

        if len(files) == 1:
            return files

        if len(files) <= LINEAR_THRESHOLD:
            return [f for f in files if self._scan([f])]

        middle = len(files) // 2
        left = self._find(files[:middle])
        right = self._find(files[middle:])
        return left + right
