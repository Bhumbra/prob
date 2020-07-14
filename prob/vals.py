"""
An abstract values class that defines a variable support set along and supports
invertible transformations.
"""

#-------------------------------------------------------------------------------
from abc import ABC, abstractmethod
import numpy as np
from prob.vtypes import eval_vtype
from prob.func import Func

#-------------------------------------------------------------------------------
DEFAULT_VSET = {False, True}

#-------------------------------------------------------------------------------
class _Vals (ABC):

  # Protected
  _vset = None      # Variable set (array or 2-length tuple range)
  _vtype = None     # Variable type
  _vfun = None      # 2-length tuple of mutually inverting functions

#-------------------------------------------------------------------------------
  def __init__(self, vset=None, 
                     vtype=None,
                     vfun=None,
                     *args,
                     **kwds):
    self.set_vset(vset, vtype)
    self.set_vfun(vfun, *args, **kwds)

#-------------------------------------------------------------------------------
  def set_vset(self, vset=None, vtype=None):

    # Default vset to nominal
    if vset is None: 
      vset = list(DEFAULT_VSET)
    elif isinstance(vset, (set, range)):
      vset = list(vset)
    elif np.iscalar(self._vset):
      vset = [self._vset]

    # At this point, self._vset should be a list, tuple, or np.ndarray
    if vtype is None:
      vset = np.array(vset)
      vtype = eval_vtype(vset)
    else:
      vset = np.array(vset, dtype=vtype)
    self._vset = set(vset)
    self._vtype = eval_vtype(vtype)
    return self._vtype

#-------------------------------------------------------------------------------
  def set_vfun(self, vfun=None, *args, **kwds):
    self._vfun = vfun
    if self._vfun is None:
      return

    assert self._vtype in (float, np.dtype('float32'),  np.dtype('float64')), \
        "Values transformation function only supported for floating point"
    message = "Input vfun be a two-sized tuple of callable functions"
    assert isinstance(self._vfun, tuple), message
    assert len(self._vfun) == 2, message
    assert callable(self._vfun[0]), message
    assert callable(self._vfun[1]), message
    self._vfun = Func(self._vfun, *args, **kwds)

#-------------------------------------------------------------------------------
  def ret_vtype(self):
    return self._vtype

#-------------------------------------------------------------------------------
  def ret_vfun(self, index=None):
    if self._vfun is None or index is None:
      return self._vfun
    return self._vfun[index]

#-------------------------------------------------------------------------------
  def get_bounds(self):
    if self._vset is None:
      return None
    lo, hi = min(self._vset), max(self._vset)
    return lo, hi

#-------------------------------------------------------------------------------
  def eval_vals(self, values=None):

    # Default to arrays of complete sets
    if values is None:
      values = np.array(list(self._vset), dtype=self._vtype)

    # Sets may be used to sample from support sets
    elif isinstance(values, set):
      assert len(values) == 1, "Set values must contain one integer"
      number = int(list(values)[0])

      # Non-continuous
      if self._vtype not in [float, np.dtype('float32'), np.dtype('float64')]:
        values = np.array(list(self._vset), dtype=self._vtype)
        divisor = len(self._vset)
        if number >= 0:
          indices = np.arange(number, dtype=int) % divisor
        else:
          indices = np.random.permutation(-number, dtype=int) % divisor
        values = values[indices]
       
      # Continuous
      else:
        lo, hi = self.get_bounds()
        lohi = np.atleast_1d([lo, hi])
        assert np.all(np.isfinite(lohi)), \
            "Cannot evaluate {} values for bounds: {}".format(values, vset)
        if self._vfun:
          lims = self.ret_vfun(0)(lohi)
          lo, hi = float(min(lims)), float(max(lims))
        if number >= 0:
          values = np.linspace(lo, hi, number + 2)[1:-1]
        else:
          values = np.random.uniform(lo, hi, size=-number)
        if self._vfun:
          return self.ret_vfun(1)(values)
        return values
    return values
   
#-------------------------------------------------------------------------------
  @abstractmethod
  def __call__(self, *args, **kwds):
    pass

#-------------------------------------------------------------------------------
