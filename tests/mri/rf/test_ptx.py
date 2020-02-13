import unittest
import numpy as np
import sigpy as sp
import numpy.testing as npt
import scipy.ndimage.filters as filt

from sigpy.mri import rf, linop, sim

if __name__ == '__main__':
    unittest.main()


class TestPtx(unittest.TestCase):

    @staticmethod
    def problem_2d(dim):
        img_shape = [dim, dim]
        sens_shape = [8, dim, dim]

        # target - slightly blurred circle
        x, y = np.ogrid[-img_shape[0] / 2: img_shape[0] - img_shape[0] / 2,
                        -img_shape[1] / 2: img_shape[1] - img_shape[1] / 2]
        circle = x * x + y * y <= int(img_shape[0] / 6) ** 2
        target = np.zeros(img_shape)
        target[circle] = 1
        target = filt.gaussian_filter(target, 1)
        target = target.astype(np.complex)

        sens = sim.birdcage_maps(sens_shape)

        return target, sens

    @staticmethod
    def problem_3d(dim, Nz):
        Nc = 8
        img_shape = [dim, dim, Nz]
        sens_shape = [Nc, dim, dim, Nz]

        # target - slightly blurred circle
        x, y, z = np.ogrid[-img_shape[0] / 2: img_shape[0] - img_shape[0] / 2,
                           -img_shape[1] / 2: img_shape[1] - img_shape[1] / 2,
                           -img_shape[2] / 2: img_shape[2] - img_shape[2] / 2]
        circle = x * x + y * y + z * z <= int(img_shape[0] / 5) ** 2
        target = np.zeros(img_shape)
        target[circle] = 1
        target = filt.gaussian_filter(target, 1)
        target = target.astype(np.complex)
        sens = sp.mri.sim.birdcage_maps(sens_shape)

        return target, sens

    def test_stspa_radial(self):

        target, sens = self.problem_2d(8)

        # makes dim*dim*2 trajectory
        traj = sp.mri.radial((sens.shape[1], sens.shape[1], 2),
                             target.shape, golden=True, dtype=np.float)
        # reshape to be Nt*2 trajectory
        traj = np.reshape(traj, [traj.shape[0]*traj.shape[1], 2])

        A = linop.Sense(sens, coord=traj,
                        weights=None, ishape=target.shape).H

        pulses = rf.stspa(target, sens, traj, dt=4e-6, alpha=1,
                          B0=None, pinst=float('inf'), pavg=float('inf'),
                          explicit=False, max_iter=100, tol=1E-4)

        npt.assert_array_almost_equal(A*pulses, target, 1E-3)

    def test_stspa_spiral(self):

        target, sens = self.problem_2d(8)

        dim = target.shape[0]
        traj = sp.mri.spiral(fov=dim / 2, N=dim,
                             f_sampling=1, R=1, ninterleaves=1, alpha=1,
                             gm=0.03, sm=200)

        A = linop.Sense(sens, coord=traj, ishape=target.shape).H

        pulses = rf.stspa(target, sens, traj, dt=4e-6, alpha=1,
                          B0=None, pinst=float('inf'), pavg=float('inf'),
                          explicit=False, max_iter=100, tol=1E-4)

        npt.assert_array_almost_equal(A*pulses, target, 1E-3)

    def test_stspa_2d_explicit(self):
        target, sens = self.problem_2d(8)
        dim = target.shape[0]
        g, k1, t, s = rf.spiral_arch(0.24, dim, 4e-6, 200, 0.035)
        k1 = k1 / dim

        A = rf.PtxSpatialExplicit(sens, k1, dt=4e-6, img_shape=target.shape,
                                  B0=None)
        pulses = sp.mri.rf.stspa(target, sens, pavg=np.Inf,
                                 pinst=np.Inf, coord=k1, dt=4e-6,
                                 max_iter=100, alpha=10, tol=1E-4,
                                 phase_update_interval=200, explicit=True)

        npt.assert_array_almost_equal(A*pulses, target, 1E-3)

    def test_stspa_3d_explicit(self):
        Nz = 3
        target, sens = self.problem_3d(3, Nz)
        dim = target.shape[0]

        g, k1, t, s = rf.spiral_arch(0.24, dim, 4e-6, 200, 0.035)
        k1 = k1 / dim

        k1 = rf.stack_of(k1, Nz, 0.1)
        A = rf.linop.PtxSpatialExplicit(sens, k1, dt=4e-6,
                                        img_shape=target.shape, B0=None)

        pulses = sp.mri.rf.stspa(target, sens, pavg=np.Inf, pinst=np.Inf,
                                 coord=k1,
                                 dt=4e-6, max_iter=30, alpha=10, tol=1E-3,
                                 phase_update_interval=200, explicit=True)

        npt.assert_array_almost_equal(A*pulses, target, 1E-3)

    def test_stspa_3d_nonexplicit(self):
        Nz = 3
        target, sens = self.problem_3d(3, Nz)
        dim = target.shape[0]

        g, k1, t, s = rf.spiral_arch(0.24, dim, 4e-6, 200, 0.035)
        k1 = k1 / dim

        k1 = rf.stack_of(k1, Nz, 0.1)
        A = sp.mri.linop.Sense(sens, k1, weights=None, tseg=None,
                               ishape=target.shape).H

        pulses = sp.mri.rf.stspa(target, sens, pavg=np.Inf, pinst=np.Inf,
                                 coord=k1,
                                 dt=4e-6, max_iter=30, alpha=10, tol=1E-3,
                                 phase_update_interval=200, explicit=False)

        npt.assert_array_almost_equal(A*pulses, target, 1E-3)