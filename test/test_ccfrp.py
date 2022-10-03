import pytest
import sys
import pandas as pd
sys.path.append('../src/')
from ccfrp.ccfrp import Ccfrp

@pytest.fixture(autouse=False)
def ccfrp():
    ccfrp=Ccfrp()
    yield ccfrp

def test_ccfrp(ccfrp):
    assert isinstance(ccfrp.effort, pd.DataFrame)
    assert isinstance(ccfrp.length, pd.DataFrame)
    assert isinstance(ccfrp.species, pd.DataFrame)
    assert isinstance(ccfrp.location, pd.DataFrame)
    try:
        assert ccfrp.effort.Date.dt
    except AttributeError:
        print("Date column should be a datetime object")
        raise
    try:
        assert ccfrp.length.Date.dt
    except AttributeError:
        print("Date column should be a datetime object")
        raise


