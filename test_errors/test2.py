"""Test file 2 with different errors."""
import os, sys  # E401 - multiple imports on one line
from pathlib import Path  # F401 - unused


def another_bad(x,y,z ):  # E203, E231 - spacing issues
    """Another function with issues."""
    result=x+y+z  # E225
    items=[1,2,3]  # E231
    return result,items  # E231


def function_too_long():
    """Function with long line."""
    very_long_string = "This is a very long string that exceeds the maximum line length and should trigger a line too long error for the linter to catch"  # E501
    return very_long_string


class AnotherBad:
    pass  # Empty class

