import unittest
from abc import ABC


def complement_slices(slices):
    if not slices:
        return [slice(None)]

    # Sort slices by start (None treated as 0)
    slices = sorted(slices, key=lambda sl: sl.start or 0)
    result = []
    last_end = 0

    for sl in slices:
        start = sl.start or 0
        stop = sl.stop

        if start > last_end:
            result.append(slice(last_end, start))

        if stop is None:
            return result  # open-ended slice ends everything

        last_end = max(last_end, stop)

    result.append(slice(last_end, None))
    return result


def __resolve_slice(slc, context_length):
    start, stop, step = slc.indices(context_length)
    return range(start, stop, step)


def coverage_set(slices, context_length):
    covered = set()
    for sl in slices:
        covered.update(__resolve_slice(sl, context_length))
    return covered


def slice_lists_equivalent_in_context(list1, list2, context):
    set1 = coverage_set(list1, len(context))
    set2 = coverage_set(list2, len(context))
    return set1 == set2


class TestComplementSlices(unittest.TestCase):
    def assertSlicesEquivalentInContext(self, slices1, slices2, context):
        if not slice_lists_equivalent_in_context(slices1, slices2, context):
            self.fail(f"Slices differ in context '{context}':\n  {slices1}\n  {slices2}")

    def assertDoubleComplementIdentity(self, original, context):
        recovered = complement_slices(complement_slices(original))
        self.assertSlicesEquivalentInContext(recovered, original, context)

    def test_basic(self):
        s = "abcdefg"
        original = [slice(1, 2), slice(4, 5)]
        complement = complement_slices(original)
        self.assertEqual(apply(s, complement), ['a', 'cd', 'fg'])
        self.assertDoubleComplementIdentity(original, s)

    def test_empty(self):
        original = []
        s = "hello"
        complement = complement_slices(original)
        self.assertEqual(apply(s, complement), ['hello'])
        self.assertDoubleComplementIdentity(original, s)

    def test_full_slice(self):
        original = [slice(None)]
        s = "hello"
        complement = complement_slices(original)
        self.assertEqual(apply(s, complement), [])
        self.assertDoubleComplementIdentity(original, s)

    def test_open_start(self):
        original = [slice(None, 3)]
        s = "abcdefg"
        complement = complement_slices(original)
        self.assertEqual(apply(s, complement), ['defg'])
        self.assertDoubleComplementIdentity(original, s)

    def test_open_end(self):
        original = [slice(3, None)]
        s = "abcdefg"
        complement = complement_slices(original)
        self.assertEqual(apply(s, complement), ['abc'])
        self.assertDoubleComplementIdentity(original, s)

    def test_single_middle_slice(self):
        original = [slice(2, 5)]
        s = "abcdefg"
        complement = complement_slices(original)
        self.assertEqual(apply(s, complement), ['ab', 'fg'])
        self.assertDoubleComplementIdentity(original, s)

    def test_adjacent_slices(self):
        original = [slice(0, 2), slice(2, 4)]
        s = "abcdef"
        complement = complement_slices(original)
        self.assertEqual(apply(s, complement), ['ef'])
        self.assertDoubleComplementIdentity(original, s)

    def test_unsorted_slices(self):
        original = [slice(3, 4), slice(1, 2)]
        s = "abcdef"
        complement = complement_slices(original)
        self.assertEqual(apply(s, complement), ['a', 'c', 'ef'])
        self.assertDoubleComplementIdentity(original, s)

    def test_final_slice_open(self):
        original = [slice(2, 3), slice(5, None)]
        s = "abcdefg"
        complement = complement_slices(original)
        self.assertEqual(apply(s, complement), ['ab', 'de'])
        self.assertDoubleComplementIdentity(original, s)


def apply(s, slices):
    return [s[sl] for sl in slices]


if __name__ == '__main__':
    unittest.main()