"""Tests for the bisecting search.

The scanner is injected, so these run without the Snyk CLI and without network.
Each fake scanner records the subsets it was asked about, which is what lets the
tests assert scan *counts* — the entire point of the strategy is doing fewer
scans, so a change that finds the right files inefficiently should still fail.
"""
import os
import tempfile
import unittest

from snyk_code_debug.bisect import (
    Bisector, ScanBudgetExceeded, cost_estimate, default_max_depth)


class FakeScanner:
    """Reports a folder dirty when any file in it has bad *content*.

    Matching on content rather than filename mirrors what the real scanner does
    and, more practically, survives staging: Bisector renames files to
    `<index>_<basename>` and the index restarts within each subset, so no name
    is stable across scans.
    """

    def __init__(self, bad_files):
        self.bad = {_marker(f) for f in bad_files}
        self.calls = 0

    def __call__(self, folder):
        self.calls += 1
        for name in os.listdir(folder):
            with open(os.path.join(folder, name)) as handle:
                if handle.read().strip() in self.bad:
                    return True
        return False


def _marker(path):
    """Stable per-file content written into the fixture and matched on."""
    return f'// {os.path.abspath(path)}'


class BisectTestCase(unittest.TestCase):

    def make_files(self, count):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        paths = []
        for index in range(count):
            path = os.path.join(folder.name, f'file{index:03d}.cpp')
            with open(path, 'w') as handle:
                handle.write(_marker(path) + '\n')
            paths.append(path)
        return paths


class TestDefaultMaxDepth(unittest.TestCase):

    def test_tiny_sets_do_not_bisect(self):
        for count in (0, 1, 2, 3, 20):
            self.assertEqual(default_max_depth(count), 0)

    def test_depth_grows_with_file_count(self):
        depths = [default_max_depth(n) for n in (50, 200, 1000, 5000)]
        self.assertEqual(depths, sorted(depths))
        self.assertLess(depths[0], depths[-1])

    def test_worst_case_stays_near_linear(self):
        """The bound exists to stop the dense case costing ~2x a linear scan."""
        for count in (50, 141, 243, 592, 2000):
            _best, worst = cost_estimate(count, default_max_depth(count))
            self.assertLessEqual(worst, count * 1.6, f'{count} files overshoots')

    def test_single_failure_still_far_cheaper_than_linear(self):
        for count in (141, 243, 592, 2000):
            best, _worst = cost_estimate(count, default_max_depth(count))
            self.assertLess(best, count / 3, f'{count} files loses too much upside')

    def test_default_is_actually_applied_end_to_end(self):
        # A depth of 0 would mean one grouped scan then every file, so the
        # count distinguishes the default from the unbounded search.
        self.assertGreater(default_max_depth(256), 0)


class TestBisector(BisectTestCase):

    def test_empty_input_does_not_scan(self):
        scanner = FakeScanner([])
        self.assertEqual(Bisector(scanner).find([]), [])
        self.assertEqual(scanner.calls, 0)

    def test_all_clean_costs_one_scan(self):
        files = self.make_files(64)
        scanner = FakeScanner([])
        bisector = Bisector(scanner)

        self.assertEqual(bisector.find(files), [])
        # The whole point: 64 clean files, one scan.
        self.assertEqual(scanner.calls, 1)

    def test_finds_single_bad_file(self):
        files = self.make_files(64)
        scanner = FakeScanner([files[40]])
        self.assertEqual(Bisector(scanner).find(files), [files[40]])

    def test_single_bad_file_in_64_is_far_cheaper_than_linear(self):
        files = self.make_files(64)
        scanner = FakeScanner([files[40]])
        bisector = Bisector(scanner)
        bisector.find(files)
        self.assertLess(scanner.calls, 20, 'bisection should beat 64 linear scans')

    def test_finds_multiple_bad_files(self):
        files = self.make_files(32)
        bad = [files[0], files[15], files[31]]
        scanner = FakeScanner(bad)
        self.assertEqual(Bisector(scanner).find(files), sorted(bad))

    def test_finds_adjacent_bad_files(self):
        # Adjacent failures land in the same leaf and exercise the
        # LINEAR_THRESHOLD branch rather than pure halving.
        files = self.make_files(16)
        bad = [files[7], files[8]]
        self.assertEqual(Bisector(FakeScanner(bad)).find(files), sorted(bad))

    def test_every_file_bad(self):
        # The pathological case: nothing is ever pruned.
        files = self.make_files(8)
        self.assertEqual(Bisector(FakeScanner(files)).find(files), sorted(files))

    def test_first_and_last_bad(self):
        files = self.make_files(16)
        bad = [files[0], files[15]]
        self.assertEqual(Bisector(FakeScanner(bad)).find(files), sorted(bad))

    def test_single_file_input(self):
        files = self.make_files(1)
        self.assertEqual(Bisector(FakeScanner(files)).find(files), files)
        self.assertEqual(Bisector(FakeScanner([])).find(files), [])

    def test_duplicate_basenames_across_directories(self):
        """Two files sharing a basename must not overwrite each other."""
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        paths = []
        for sub in ('a', 'b'):
            os.makedirs(os.path.join(root.name, sub))
            path = os.path.join(root.name, sub, 'main.cpp')
            with open(path, 'w') as handle:
                handle.write(_marker(path) + '\n')
            paths.append(path)

        # Only b/main.cpp is bad. Without the index prefix when staging, the two
        # identically-named files would collide in the temp folder and one would
        # never be tested.
        found = Bisector(FakeScanner([paths[1]])).find(paths)
        self.assertEqual(found, [paths[1]])

    def test_max_scans_raises_with_partial_results(self):
        files = self.make_files(64)
        scanner = FakeScanner(files)  # everything bad, so it never prunes
        with self.assertRaises(ScanBudgetExceeded) as caught:
            Bisector(scanner, max_scans=5).find(files)
        self.assertEqual(caught.exception.scans, 5)

    def test_max_depth_falls_back_to_per_file_scans(self):
        files = self.make_files(16)
        bad = [files[2], files[9]]
        # depth 1 leaves two subsets of 8; each dirty one is then scanned per file.
        scanner = FakeScanner(bad)
        self.assertEqual(Bisector(scanner, max_depth=1).find(files), sorted(bad))
        # 1 root + 2 halves + 16 individual = 19
        self.assertEqual(scanner.calls, 19)

    def test_max_depth_zero_is_linear_after_one_scan(self):
        files = self.make_files(8)
        bad = [files[5]]
        scanner = FakeScanner(bad)
        self.assertEqual(Bisector(scanner, max_depth=0).find(files), bad)
        self.assertEqual(scanner.calls, 9)

    def test_max_depth_still_short_circuits_a_clean_tree(self):
        files = self.make_files(32)
        scanner = FakeScanner([])
        self.assertEqual(Bisector(scanner, max_depth=0).find(files), [])
        self.assertEqual(scanner.calls, 1)

    def test_max_depth_beats_unbounded_when_failures_are_dense(self):
        files = self.make_files(16)
        unbounded = FakeScanner(files)
        Bisector(unbounded).find(files)
        bounded = FakeScanner(files)
        Bisector(bounded, max_depth=0).find(files)
        self.assertLess(bounded.calls, unbounded.calls)

    def test_staging_hard_links_rather_than_copying(self):
        """Bisection re-stages the same file once per level of the search.

        Copying would rewrite the tree several times per run. A hard link shares
        the inode, so the check is that the staged entry resolves to the same
        inode as the source rather than a fresh one.
        """
        files = self.make_files(8)
        source_inodes = {os.stat(f).st_ino for f in files}
        staged_inodes = []

        def scanner(folder):
            for name in os.listdir(folder):
                staged_inodes.append(os.stat(os.path.join(folder, name)).st_ino)
            return False

        Bisector(scanner).find(files)
        self.assertTrue(staged_inodes, 'nothing was staged')
        self.assertTrue(
            set(staged_inodes) <= source_inodes,
            'staged files got new inodes, so they were copied not linked')

    def test_falls_back_to_copy_when_linking_is_impossible(self):
        """A source that cannot be hard-linked must still be scanned."""
        files = self.make_files(4)
        seen = []

        original_link = os.link

        def refuse_link(src, dst):
            raise OSError('cross-device link not permitted')

        os.link = refuse_link
        self.addCleanup(setattr, os, 'link', original_link)

        def scanner(folder):
            seen.append(sorted(os.listdir(folder)))
            return False

        self.assertEqual(Bisector(scanner).find(files), [])
        self.assertEqual(len(seen[0]), 4, 'copy fallback did not stage every file')

    def test_on_scan_callback_receives_progress(self):
        files = self.make_files(8)
        seen = []
        Bisector(FakeScanner([files[3]]), on_scan=lambda n, size: seen.append((n, size))).find(files)
        self.assertEqual([n for n, _ in seen], list(range(1, len(seen) + 1)))
        self.assertEqual(seen[0][1], 8)


if __name__ == '__main__':
    unittest.main()
