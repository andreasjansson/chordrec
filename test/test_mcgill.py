import numpy as np
import unittest2 as unittest
from chordrec import mcgill

class TestMcGill(unittest.TestCase):

    def test_align(self):
        beats = [mcgill.Beat(start=i * 10, end=(i + 1) * 10)
                 for i in range(6)]
        x = [(0, 8, 'a'),
             (9, 10, 'b'),
             (10, 12, 'c'),
             (12, 17, 'd'),
             (17, 26, 'e'),
             (26, 46, 'f')]
        expected = ['a', 'd', 'e', 'f', 'f', None]
        aligned = mcgill.beat_align(beats, x)
        self.assertEquals(aligned, expected)

    def test_align_average(self):
        beats = [mcgill.Beat(start=i * 10, end=(i + 1) * 10)
                 for i in range(6)]
        x = [(0, 8, np.array([0, 0])),    # a
             (9, 10, np.array([10, 0])),  # b
             (10, 12, np.array([5, 5])),  # c
             (12, 17, np.array([0, 10])), # d
             (17, 26, np.array([2, 0])),  # e
             (26, 46, np.array([10, 10]))]# f
        expected = [[1, 0], [1.6, 6], [5.2, 4], [10, 10], [6, 6], [0, 0]]

        aligned = mcgill.beat_align(beats, x, average=True)
        aligned = [a.tolist() for a in aligned]
        self.assertEquals(aligned, expected)
