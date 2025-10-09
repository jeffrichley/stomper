"""Test file 1 with intentional errors."""
import unused_module  # F401 - unused import
import os  # F401 - unused import


def bad_function( ):  # E201 - whitespace after '('
    """Function with spacing issues."""
    x=1+2  # E225 - missing whitespace around operator
    y = 3+4  # E226 - missing whitespace
    result=x+y  # E225
    return result


class BadClass:
    """Class with issues."""
    
    def method(self,x,y ):  # E203 - whitespace before ')'
        """Method with issues."""
        data=[1,2,3,4,5]  # E231 - missing whitespace after ','
        return data


if __name__=="__main__":  # E225 - missing whitespace
    bad_function()

