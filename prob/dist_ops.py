
# A module to perform operations on Dist() instances.

#-------------------------------------------------------------------------------
import collections
import numpy as np
from prob.vtypes import isscalar
from prob.ptypes import rescale, prod_ptype, prod_rule, iscomplex

#-------------------------------------------------------------------------------
def str2key(string):
  if isinstance(string, str):
    k = string.find('=')
    if k > 0:
      return string[:k]
    return string
  return [str2key(element) for element in string]

#-------------------------------------------------------------------------------
def str_margcond(name=None):
  """ Returns (marg,cond) tuple of OrderedDicts from a name """
  marg_str = name
  marg = collections.OrderedDict()
  cond = collections.OrderedDict()
  if not marg_str:
    return marg, cond
  lt_paren = marg_str.find('(')
  rt_paren = marg_str.find(')')
  if lt_paren >= 0 or rt_paren >= 0:
    assert lt_paren >= 0 and rt_paren > lt_paren, \
      "Unmatched parenthesis in name"
    marg_str = marg_str[lt_paren:1:rt_paren]
  cond_str = ''
  if '|' in marg_str:
    split_str = name.split('|')
    assert len(split_str) == 2, "Ambiguous name: {}".format(name)
    marg_str, cond_str = split_str
  marg_strs = []
  cond_strs = []
  if len(marg_str):
    marg_strs = marg_str.split(',') if ',' in marg_str else [marg_str]
  if len(cond_str):
    cond_strs = cond_str.split(',') if ',' in cond_str else [cond_str]
  for string in marg_strs:
    marg.update({str2key(string): string})
  for string in cond_strs:
    cond.update({str2key(string): string})
  return marg, cond

#-------------------------------------------------------------------------------
def margcond_str(marg, cond):
  """ Returns a name from OrderedDict values in marg and cond """
  marg = list(marg.values()) if isinstance(marg, dict) else list(marg)
  cond = list(cond.values()) if isinstance(cond, dict) else list(cond)
  marg_str = ','.join(marg)
  cond_str = ','.join(cond)
  return '|'.join([marg_str, cond_str]) if cond_str else marg_str

#-------------------------------------------------------------------------------
def prod_dist(*args, **kwds):
  """ Multiplies two or more distributions subject to the following:
  1. They must not share the same marginal variables. 
  2. Conditional variables must be identical unless contained as marginal from
     another distribution.
  """
  # Check ptypes, scalars, possible fasttrack
  if not len(args):
    return None
  dist_obj = type(args[0])
  kwds = dict(kwds)
  ptypes = [arg.ret_ptype() for arg in args]
  ptype = kwds.get('ptype', None) or prod_ptype(ptypes)
  arescalars = [arg.ret_isscalar() for arg in args]
  maybe_fasttrack = all(arescalars) and \
                    np.all(ptype == np.array(ptypes)) and \
                    ptype in [0, 1.]
  vals = [arg.vals for arg in args]
  probs = [arg.prob for arg in args]

  # Extract marginal and conditional names
  marg_names = [arg.ret_marg_names() for arg in args]
  cond_names = [arg.ret_cond_names() for arg in args]
  prod_marg = [name for dist_marg_names in marg_names \
                          for name in dist_marg_names]
  assert len(prod_marg) == len(set(prod_marg)), \
      "Marginal variable names not unique across distributions: {}".\
      format(prod_marg)
  prod_marg_name = ','.join(prod_marg)

  # Maybe fast-track identical conditionals
  if maybe_fasttrack:
    if not any(cond_names) or len(set(cond_names)) == 1:
      cond_names = cond_names[0]
      if not cond_names or \
          len(set(cond_names).union(prod_marg)) == len(cond_names) + len(prod_marg):
        prod_cond_name = ','.join(cond_names)
        prod_name = '|'.join([prod_marg_name, prod_cond_name])
        prod_vals = collections.OrdereDict()
        [prod_vals.update(val) for val in vals]
        prob = float(sum(probs)) if iscomplex(ptype) else float(np.prod(probs))
        return dist_obj(prod_name, prod_vals, prob, ptype)

   # Check cond->marg accounts for all differences between conditionals
  flat_cond_names = [name for dist_cond_names in cond_names \
                          for name in dist_cond_names]
  cond2marg = [cond_name for cond_name in flat_cond_names \
                         if cond_name in prod_marg]
  prod_cond = [cond_name for cond_name in flat_cond_names \
                         if cond_name not in cond2marg]
  cond2marg_set = set(cond2marg)

  # Check conditionals compatible
  prod_cond_set = set(prod_cond)
  cond2marg_dict = {name: None for name in prod_cond}
  for i, arg in enumerate(args):
    cond_set = set(cond_names[i]) - cond2marg_set
    assert prod_cond_set == cond_set, \
        "Incompatible conditionals {} vs {}: ".format(prod_cond_set, cond_set)
    for name in cond2marg:
      if name in arg.vals:
        values = arg.vals[name]
        if cond2marg_dict[name] is None:
          cond2marg_dict[name] = values
        elif not np.allclose(cond2marg_dict[name], values):
          raise ValueError("Mismatch in values for condition {}".format(name))

  # Establish product name, values, and dimensions
  prod_keys = str2key(prod_marg + prod_cond)
  prod_nkeys = len(prod_keys)
  prod_arescalars = np.zeros(prod_nkeys, dtype=bool)
  prod_cond_name = ','.join(prod_cond)
  prod_name = '|'.join([prod_marg_name, prod_cond_name])
  prod_vals = collections.OrderedDict()
  for i, key in enumerate(prod_keys):
    values = None
    for val in vals:
      if key in val.keys():
        values = val[key]
        break
    assert values is not None, "Values for key {} not found".format(key)
    prod_arescalars[i] = isscalar(values)
    prod_vals.update({key: values})
  prod_cdims = np.cumsum(np.logical_not(prod_arescalars))
  prod_ndims = prod_cdims[-1]

  # Fast-track scalar products
  if maybe_fasttrack and prod_ndims == 0:
     prob = float(sum(probs)) if iscomplex(ptype) else float(np.prod(probs))
     return dist(prod_name, prod_vals, prob, ptype)

  # Exclude shared dimensions
  for arg in args:
    dims = [dim for dim in arg.dims.values() if dim is not None]
    assert len(dims) == len(set(dims)), \
        "Shared dimensionality not yet supported for prod_dist :("

  # Reshape values - they require no axes swapping
  ones_ndims = np.ones(prod_ndims, dtype=int)
  prod_dims = np.ones(prod_ndims, dtype=int)
  scalarset = set()
  dimension = collections.OrderedDict()
  for i, key in enumerate(prod_keys):
    if prod_arescalars[i]:
      scalarset += {key}
    else:
      values = prod_vals[key]
      re_shape = np.copy(ones_ndims)
      dim = prod_cdims[i]-1
      dimension.update({key: dim})
      re_shape[dim] = values.size
      prod_dims[dim] = values.size
      prod_vals.update({key: values.reshape(re_shape)})
  
  # Match probability axes and shapes with axes swapping then reshaping
  prod_probs = [None] * len(args)
  for i, prob in enumerate(probs):
    if not isscalar(prob):
      val_names = str2key(marg_names[i] + cond_names[i])
      nonscalars = [val_name for val_name in val_names \
                             if val_name not in scalarset]
      dims = np.array([dimension[name] for name in nonscalars])
      if dims.size > 1 and np.min(np.diff(dims)) < 0:
        swap = np.argsort(dims)
        probs[i] = np.swapaxes(prob, list(range(dims)), swap)
        dims = dims[swap]
      re_shape = np.copy(ones_ndims)
      for dim in dims:
        re_shape[dim] = prod_dims[dim]
      probs[i] = probs[i].reshape(re_shape)

  # Multiply the probabilities and output the result as a distribution instance
  prob, ptype = prod_rule(*tuple(probs), ptypes=ptypes, ptype=ptype)

  return dist_obj(prod_name, prod_vals, prob, ptype)


#-------------------------------------------------------------------------------
def sum_dist(*args):
  """ Quick and dirty concatenation """
  if not len(args):
    return None
  dist_obj = type(args[0])
  ptypes = [arg.ret_ptype() for arg in args]
  vals = [arg.vals for arg in args]
  probs = [arg.prob for arg in args]

  # Extract marginal and conditional names
  marg_names = [str2key(arg.ret_marg_names()) for arg in args]
  cond_names = [str2key(arg.ret_cond_names()) for arg in args]

  assert len(marg_names) == len(set(marg_names)), \
      "Marginal variable names not identical across distributions: {}".\
      format(marg_names)
  marg_names = marg_names[0]

  assert len(cond_names) == len(set(cond_names)), \
      "Conditional variable names not identical across distributions: {}".\
      format(cond_names)
  cond_names = cond_names[0]
  sum_names = marg_names + cond_names

  # Find concatenation dimension
  sum_name = args[0].ret_name()
  sum_ptype = args.ret_ptype[0]
  sum_vals = collections.OrderedDict(vals[0])
  sum_dim = [None] * (len(args) - 1)
  for i, arg in enumerate(args):
    if i == 0:
      continue
    for key in marg_names:
      if sum_dim[i-1] is not None:
        continue
      elif not arg.ret_isscalar(key):
        key_vals = arg.vals[key]
        if key_vals.size == sum_vals[key].size:
          if np.allclose(key_vals, sum_vals[key]):
            continue
        sum_dim[i-1] = arg.ret_dimension(key)
  
  assert len(set(sum_dim)) == 1, "Cannot find unique concatenation axis"
  key = marg_names[sum_dim]
  sum_dim = sum_dim[0]
  sum_prob = np.copy(probs[0])
  for i, val in enumerate(vals):
    if i == 0:
      continue
    sum_vals[key] = np.concatenate([sum_vals[key], val[key]], axis=sum_dim)
    sub_prob = np.concatenate([sum_prob, probs[i]], axis=sum_dim)

  return dist_obj(sum_name, sum_vals, sum_prob, sum_ptype)

#-------------------------------------------------------------------------------
