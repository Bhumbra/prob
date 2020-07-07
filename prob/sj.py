"""
A stochastic junction comprises a collection of a random variables that 
participate in a joint probability distribution function.
"""
#-------------------------------------------------------------------------------
import warnings
import collections
import numpy as np
from prob.rv import RV
from prob.dist import Dist
from prob.vtypes import isscalar
from prob.pscales import eval_pscale, prod_pscale, prod_rule
from prob.func import Func

#-------------------------------------------------------------------------------
class SJ:

  # Protected
  _name = None      # Cannot be set externally
  _rvs = None       # Dict of random variables
  _nrvs = None
  _keys = None
  _keyset = None
  _defiid = None
  _pscale = None
  _arg_order = None
  _as_scalar = None # dictionary of bools
  _prob = None
  _prob_args = None
  _prob_kwds = None
  _pscale = None

  # Private
  __callable = None

#-------------------------------------------------------------------------------
  def __init__(self, *args):
    self.set_rvs(*args)
    self.set_prob()

#-------------------------------------------------------------------------------
  def set_rvs(self, *args):
    if len(args) == 1 and isinstance(args[0], (SJ, dict, set, tuple, list)):
      args = args[0]
    else:
      args = tuple(args)
    self.add_rv(args)
    return self.ret_rvs()

#-------------------------------------------------------------------------------
  def add_rv(self, rv):
    assert self._prob is None, \
      "Cannot assign new randon variables after specifying joint/condition prob"
    if self._rvs is None:
      self._rvs = collections.OrderedDict()
    if isinstance(rv, (SJ, dict, set, tuple, list)):
      rvs = rv
      if isinstance(rvs, SJ):
        rvs = rvs.ret_rvs()
      if isinstance(rvs, dict):
        rvs = rvs.values()
      [self.add_rv(rv) for rv in rvs]
    else:
      key = rv.ret_name()
      assert isinstance(rv, RV), \
          "Input not a RV instance but of type: {}".format(type(rv))
      assert key not in self._rvs.keys(), \
          "Existing RV name {} already present in collection".format(rv_name)
      self._rvs.update({key: rv})
    self._nrvs = len(self._rvs)
    self._keys = list(self._rvs.keys())
    self._keyset = set(self._keys)
    self._defiid = self._keyset
    self._name = ','.join(self._keys)
    self.set_pscale()
    return self._nrvs
  
#-------------------------------------------------------------------------------
  def ret_rvs(self, aslist=True):
    # Defaulting aslist=True plays more nicely with inheriting classes
    rvs = self._rvs
    if aslist:
      if isinstance(rvs, dict):
        rvs = list(rvs.values())
      assert isinstance(rvs, list), "RVs not a recognised variable type: {}".\
                                    format(type(rvs))
    return rvs

#-------------------------------------------------------------------------------
  def ret_name(self):
    return self._name

#-------------------------------------------------------------------------------
  def ret_nrvs(self):
    return self._nrvs

#-------------------------------------------------------------------------------
  def ret_keys(self):
    return self._keys

#-------------------------------------------------------------------------------
  def ret_keyset(self):
    return self._keyset

#-------------------------------------------------------------------------------
  def set_pscale(self, pscale=None):
    if pscale is not None or not self._nrvs:
      self._pscale = eval_pscale(pscale)
      return self._pscale
    rvs = self.ret_rvs(aslist=True)
    pscales = [rv.ret_pscale() for rv in rvs]
    self._pscale = prod_pscale(pscales)
    return self._pscale

#-------------------------------------------------------------------------------
  def ret_pscale(self):
    return self._pscale

#-------------------------------------------------------------------------------
  def set_prob(self, prob=None, *args, **kwds):
    kwds = dict(kwds)
    if 'pscale' in kwds:
      pscale = kwds.pop('pscale')
      self.set_pscale(pscale)
    self._prob = prob
    self.__callable = callable(self._prob)
    if self.__callable:
      self._prob = Func(self._prob, *args, **kwds)

#-------------------------------------------------------------------------------
  def fuse_dict(self, val_dict=None, def_val=None):
    if not val_dict:
      return collections.OrderedDict({key: def_val for key in self._keys})
    fused = collections.OrderedDict(val_dict)
    keys = []
    for key in fused.keys():
      if ',' in key:
        keys.extend(key_split)
      else:
        keys.append(key)
    for key in keys:
      assert key in self._keys, "Unknown key: {}".format(key)
    for key in self._keys:
      if key not in keys:
        fused.update({key: def_val})
    return fused

#-------------------------------------------------------------------------------
  def eval_vals(self, *args, **kwds):
    """ This ignores self._prob and self._arg_order """
    values = None
    dims = {}
    if not len(args):
      if len(kwds):
        values = self.fuse_dict(kwds)
    else:
      assert not len(kwds), "Please input args or kwds but no both"
      if len(args) == 1 and isinstance(args[0], dict):
        values = self.fuse_dict(args[0])
      else:
        assert len(args) == self._nrvs, \
            "Number of positional arguments must match number of RVs"
        values = collections.OrderedDict({key: arg \
                   for key, arg in zip(self._keys, args)})
    
    # Don't reshape if all scalars (and therefore by definition no joint keys)
    if all([np.isscalar(value) for value in values.values()]): # use np.scalar
      return values, dims

    # Share dimensions for joint variables and do not dimension scalars
    dims = collections.OrderedDict({key: i for i, key in enumerate(self._keys)})
    values_ref = collections.OrderedDict({key: [key, None] for key in self._keys})
    seen_keys = []
    for i, key in enumerate(self._keys):
      rem_keys = self._keys[(i+1):]
      if key in values.keys():
        seen_keys.append(key)
        if np.isscalar(values[key]):
          for rem_key in rem_keys:
            dims[rem_key] -= 1
      elif key not in seen_keys:
        seen_keys.append(key)
        for val_key in value.keys():
          subkeys = val_key.split(',')
          matches = 0
          for j, subkey in enumerate(subkeys):
            for rem_key in rem_keys:
              if rem_key == val_key:
                values_ref[rem_key] = [val_key, j] 
              else:
                if rem_key in subkeys:
                  seen_keys.append(key)
                  values_ref[rem_key] = [val_key, j] 
                  matches += 1
                  dims[rem_key] = dims[key]
                else:
                  dims[rem_key] -= matches

    # Reshape
    ndims = max(dims.values()) + 1
    ones_ndims = np.ones(ndims, dtype=int)
    vals = collections.OrderedDict()
    rvs = self.ret_rvs(aslist=True)
    for i, rv in enumerate(rvs):
      key = rv.ret_name()
      reshape = True
      if key in values.keys():
        vals.update({key: values[key]})
        reshape = not np.isscalar(vals[key])
        if vals[key] is None or isinstance(vals[key], set):
          vals[key] = rv.eval_vals(vals[key])
      else:
        val_ref = values_ref[key]
        vals.update({key: values[val_ref[0]][val_ref[1]]})
        dist_dict.update({key: key + "={}"})
      if reshape:
        re_shape = np.copy(ones_ndims)
        re_dim = dims[key]
        re_shape[re_dim] = vals[key].size
        vals[key] = vals[key].reshape(re_shape)
    
    # Remove dimensionality for scalars
    for key in self._keys:
      if isscalar(vals[key]):
        dims[key] = None
    return vals, dims

#-------------------------------------------------------------------------------
  def eval_prob(self, values):
    assert isinstance(values, dict), "Input to eval_prob() requires values dict"
    assert set(values.keys()) == self._keyset, \
      "Sample dictionary keys {} mismatch with RV names {}".format(
        values.keys(), self._keys())
    if self._prob is None:
      rvs = self.ret_rvs(aslist=True)
      pscales = np.array([rv.ret_pscale() for rv in rvs])
      probs = [rv.eval_prob(values[rv.ret_name()]) for rv in rvs]
      prob, pscale = prod_rule(*tuple(probs), pscales=pscales, pscale=self._pscale)
      return prob
    if not self.__callable:
      return self._prob
    return self._prob(values)

#-------------------------------------------------------------------------------
  def eval_dist_name(self, values=None):
    keys = self._keys 
    vals = values
    if isinstance(vals, dict):
      keys = vals.keys()
      assert set(keys) == self._keyset, "Missing keys in {}".format(vals.keys())
    else:
      vals = {key: vals for key in keys}
    rv_dist_names = [rv.eval_dist_name(vals[rv.ret_name()]) \
                     for rv in self._rvs.values()]
    dist_name = ','.join(rv_dist_names)
    return dist_name

#-------------------------------------------------------------------------------
  def __call__(self, values=None, **kwds):  # Let's make this args ands kwds
    ''' 
    Returns a namedtuple of the rvs.
    '''
    kwds = dict(kwds)
    iid = False if 'iid' not in kwds else kwds.pop('iid')
    if type(iid) is bool and iid:
      iid = self._defiid
    if self._rvs is None:
      return None
    if values is None and len(kwds):
      values = collections.OrderedDict(kwds)
    dist_name = self.eval_dist_name(values)
    if not isinstance(values, dict):
      values = collections.OrderedDict({key: values for key in self._keys})
    vals, dims = self.eval_vals(values)
    prob = self.eval_prob(vals)
    if not iid: 
      return Dist(dist_name, vals, dims, prob, self._pscale)
    return Dist(dist_name, vals, dims, prob, self._pscale).prod(iid)

#-------------------------------------------------------------------------------
  def __len__(self):
    return self._nrvs

#-------------------------------------------------------------------------------
  def __getitem__(self, key):
    if type(key) is int:
      key = self._keys[key]
    if isinstance(key, str):
      if key not in self._keys:
        return None
    return self._rvs[key]

#-------------------------------------------------------------------------------
