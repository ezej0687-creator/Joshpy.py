"""Check behavior with assertions and Python's unittest framework."""

import unittest


def rectangle_area(width, height):
    return width * height


class RectangleAreaTests(unittest.TestCase):
    def test_multiplies_width_by_height(self):
        self.assertEqual(rectangle_area(4, 3), 12)

    def test_zero_width_has_zero_area(self):
        self.assertEqual(rectangle_area(0, 3), 0)


if __name__ == "__main__":
    unittest.main()

"""
Exercises:
1. Add tests for a square, a decimal input, and a negative dimension.
2. Write tests for your Celsius conversion function.
3. Change a function so one test fails, then restore the correct behavior.
4. Run this lesson with: python lessons/08_testing/lesson.py
"""
