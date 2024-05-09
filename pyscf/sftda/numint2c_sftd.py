#!/usr/bin/env python
# This file can be merged into pyscf.dft.numint2c.py

MGGA_DENSITY_LAPL = False # just copy from pyscf.dft.numint2c.py

import functools
import numpy as np
from pyscf import lib
from pyscf.dft import numint

from pyscf.dft.numint2c import __mcfun_fn_eval_xc

# This function can be merged with pyscf.dft.numint2c.mcfun_eval_xc_adapter()
# This function should be a class function in the Numint2c class.
def mcfun_eval_xc_adapter_sf(ni, xc_code):
    '''Wrapper to generate the eval_xc function required by mcfun
    
    Kwargs:
        dim: int
            eval_xc_eff_sf is for mc collinear sf tddft/ tda case.add().
    '''
    
    try:
        import mcfun
    except ImportError:
        raise ImportError('This feature requires mcfun library.\n'
                          'Try install mcfun with `pip install mcfun`')

    xctype = ni._xc_type(xc_code)
    fn_eval_xc = functools.partial(__mcfun_fn_eval_xc, ni, xc_code, xctype)
    nproc = lib.num_threads()

    def eval_xc_eff(xc_code, rho, deriv=1, omega=None, xctype=None,
                verbose=None):
        return mcfun.eval_xc_eff_sf(
            fn_eval_xc, rho, deriv, 
            collinear_samples=ni.collinear_samples, workers=nproc)
    return eval_xc_eff

# This function should be a class function in the Numint2c class.
def cache_xc_kernel_sf(self, mol, grids, xc_code, mo_coeff, mo_occ, spin=1,max_memory=2000):
    '''Compute the fxc_sf, which can be used in SF-TDDFT/TDA
    '''
    xctype = self._xc_type(xc_code)
    if xctype == 'GGA':
        ao_deriv = 1
    elif xctype == 'MGGA':
        ao_deriv = 2 if MGGA_DENSITY_LAPL else 1
    else:
        ao_deriv = 0
    with_lapl = MGGA_DENSITY_LAPL
        
    assert mo_coeff[0].ndim == 2
    assert spin == 1
    
    nao = mo_coeff[0].shape[0]
    rhoa = []
    rhob = []
    
    ni = numint.NumInt()
    for ao, mask, weight, coords \
            in self.block_loop(mol, grids, nao, ao_deriv, max_memory=max_memory):
        rhoa.append(ni.eval_rho2(mol, ao, mo_coeff[0], mo_occ[0], mask, xctype, with_lapl))
        rhob.append(ni.eval_rho2(mol, ao, mo_coeff[1], mo_occ[1], mask, xctype, with_lapl))
    rho_ab = (np.hstack(rhoa), np.hstack(rhob))
    rho_ab = np.asarray(rho_ab)
    rho_tmz = np.zeros_like(rho_ab)
    rho_tmz[0] += rho_ab[0]+rho_ab[1]
    rho_tmz[1] += rho_ab[0]-rho_ab[1]
    eval_xc = mcfun_eval_xc_adapter_sf(self,xc_code)
    fxc_sf = eval_xc(xc_code, rho_tmz, deriv=2, xctype=xctype)
    return fxc_sf