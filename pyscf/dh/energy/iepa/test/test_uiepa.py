import unittest
from pyscf import gto, scf, mp, df, dft, dh
from pyscf.dh import RIEPAofDH, UIEPAofDH
import numpy as np


def get_mf_h2o_hf():
    mol = gto.Mole(atom="O; H 1 0.94; H 1 0.94 2 104.5", basis="cc-pVTZ").build()
    return scf.RHF(mol).run(conv_tol=1e-12), scf.UHF(mol).run(conv_tol=1e-12)


def get_mf_h2o_cation_hf():
    mol = gto.Mole(atom="O; H 1 0.94; H 1 0.94 2 104.5", basis="cc-pVTZ").build()
    return scf.UHF(mol).run(conv_tol=1e-12)


class TestEngUIEPA(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mf_h2o_hf_res, cls.mf_h2o_hf = get_mf_h2o_hf()
        cls.mf_h2o_cation_hf = get_mf_h2o_cation_hf()

    def test_eng_uiepa_conv_by_riepa(self):
        mf_s = self.mf_h2o_hf
        mf_s_res = self.mf_h2o_hf_res
        mf_dh = UIEPAofDH(mf_s)
        mf_dh.kernel(
            integral_scheme_iepa="conv",
            iepa_schemes=["MP2", "MP2CR", "IEPA", "SIEPA"],
            omega_list_iepa=[0, 0.7])
        mf_dh_res = RIEPAofDH(mf_s_res)
        mf_dh_res.kernel(
            integral_scheme_iepa="conv",
            iepa_schemes=["MP2", "MP2CR", "IEPA", "SIEPA"],
            omega_list_iepa=[0, 0.7])
        keys = [f"eng_corr_{scheme}" for scheme in ["MP2", "MP2CR", "IEPA", "SIEPA"]]
        keys += [dh.util.pad_omega(f"eng_corr_{scheme}", 0.7) for scheme in ["MP2", "MP2CR", "IEPA", "SIEPA"]]
        for key in keys:
            self.assertAlmostEqual(mf_dh.params.results[key], mf_dh_res.params.results[key], 8)

    def test_eng_uiepa_ri_by_riepa(self):
        mf_s = self.mf_h2o_hf
        mf_s_res = self.mf_h2o_hf_res
        mf_dh = UIEPAofDH(mf_s)
        mf_dh.kernel(
            iepa_schemes=["MP2", "MP2CR", "IEPA", "SIEPA"],
            omega_list_iepa=[0, 0.7])
        mf_dh_res = RIEPAofDH(mf_s_res)
        mf_dh_res.kernel(
            iepa_schemes=["MP2", "MP2CR", "IEPA", "SIEPA"],
            omega_list_iepa=[0, 0.7])
        keys = [f"eng_corr_{scheme}" for scheme in ["MP2", "MP2CR", "IEPA", "SIEPA"]]
        keys += [dh.util.pad_omega(f"eng_corr_{scheme}", 0.7) for scheme in ["MP2", "MP2CR", "IEPA", "SIEPA"]]
        for key in keys:
            self.assertAlmostEqual(mf_dh.params.results[key], mf_dh_res.params.results[key], 8)

    def test_eng_uiepa_coverage(self):
        # coverage only, not testing correctness
        mf_s = self.mf_h2o_cation_hf

        mf_dh = UIEPAofDH(mf_s)
        mf_dh.params.flags.update({
            "iepa_schemes": ["MP2", "MP2cr", "IEPA", "sIEPA", "DCPT2"],
            "omega_list_iepa": [0, 0.7, -0.7],
        })
        mf_dh.run().run()

        eri = mf_s._eri.copy()
        mf_s._eri = None

        mf_dh = UIEPAofDH(mf_s)
        mf_dh.kernel(integral_scheme_iepa="conv", iepa_schemes=["MP2cr", "IEPA", "sIEPA"])

        mf_dh = UIEPAofDH(mf_s)
        mf_dh.kernel(integral_scheme_iepa="ri", iepa_schemes=["IEPA", "sIEPA"])

        with self.assertRaises(ValueError):
            mf_dh.kernel(iepa_schemes="RPA")

        with self.assertRaises(NotImplementedError):
            mf_dh.kernel(iepa_schemes="MP2cr2")

        mf_s._eri = eri