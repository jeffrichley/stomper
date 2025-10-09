"""Test file 3 with more errors."""
from typing import List, Dict  # F401 - unused imports
import json  # F401


def third_function(   ):  # E201, E202 - whitespace issues
    """Third test function."""
    data=[1,2,3,4,5]  # E231
    mapping={'a':1,'b':2}  # E231
    return data


def unused_function():
    """This function is never called."""
    x=1  # E225
    y=2  # Multiple statements should be on separate lines
    return x+y


# Missing newline at end of file

