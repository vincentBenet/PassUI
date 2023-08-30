import sys
import os
import pytest

path_current = os.path.dirname(__file__)
path_package = os.path.join(path_current, "..")
sys.path.append("")
from PassUI import passpy_api


def test_init():
    assert isinstance(passpy_api.PassPy(), passpy_api.PassPy)

def test


