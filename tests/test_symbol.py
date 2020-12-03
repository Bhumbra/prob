# Module to test Expr

#-------------------------------------------------------------------------------
import pytest
import math
import numpy as np
import sympy as sy
import probayes as pb

#-------------------------------------------------------------------------------
LOG_TESTS = [(math.exp(1.),1.)]
INC_TESTS = [(3,4)]

#-------------------------------------------------------------------------------
@pytest.mark.parametrize("inp,out", LOG_TESTS)
def test_log(inp, out):
  x = pb.Variable('x', vtype=float, vset=(0, pb.OO))
  expr = sy.log(x[:])
  output = float(expr.subs({'x': inp}))
  close = np.isclose(output, out)
  if isinstance(inp, np.ndarray):
    assert np.all(close), "Output values not as expected"
  else:
    assert close, "Output value {} not as expected {}".format(output, out)

#-------------------------------------------------------------------------------
@pytest.mark.parametrize("inp,out", INC_TESTS)
def test_inc(inp, out):
  x = pb.Symbol('x')
  expr = x[:]+1
  output = int(expr.subs({'x': inp}))
  close = np.isclose(output, out)
  if isinstance(inp, np.ndarray):
    assert np.all(close), "Output values not as expected"
  else:
    assert close, "Output value {} not as expected {}".format(output, out)

#-------------------------------------------------------------------------------
