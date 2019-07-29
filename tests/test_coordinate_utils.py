import numpy as np
import os
from unittest import TestCase, main, skip
from chaosmagpy import coordinate_utils as c
from chaosmagpy import data_utils as d
from math import pi
from timeit import default_timer as timer
try:
    from tests.helpers import load_matfile
except ImportError:
    from helpers import load_matfile

ROOT = os.path.abspath(os.path.dirname(__file__))
MATFILE_PATH = os.path.join(ROOT, 'CHAOS_test.mat')

# check if mat-file exists in tests directory
if os.path.isfile(MATFILE_PATH) is False:
    MATFILE_PATH = str(input('Matfile path for coordinate_utils test?: '))


class CoordinateUtilsTestCase(TestCase):
    def setUp(self):

        print(f'\nRunning {self._testMethodName}:')

    def test_dipole_to_unit(self):

        self.assertIsNone(np.testing.assert_allclose(
            c.igrf_dipole('2010'),
            c._dipole_to_unit(11.32, 289.59)))

        self.assertIsNone(np.testing.assert_allclose(
            c.igrf_dipole('2015'),
            c._dipole_to_unit(np.array([-29442.0, -1501.0, 4797.1]))))

        self.assertIsNone(np.testing.assert_allclose(
            c.igrf_dipole('2015'),
            c._dipole_to_unit(-29442.0, -1501.0, 4797.1)))

    @skip('New conductivity model uses thinlayer approximation.')
    def _test_q_response_sphere(self):

        a = 6371.2
        n = 1

        # load matfile
        test = load_matfile(MATFILE_PATH, 'test_conducting_sphere')

        model = np.loadtxt(c.basicConfig['file.Earth_conductivity'])
        C_n_mat = np.ravel(test['C_n'])
        rho_a_mat = np.ravel(test['rho_a'])
        phi_mat = np.ravel(test['phi'])
        Q_n_mat = np.ravel(test['Q_n'])

        radius = a - model[:, 0]
        sigma = model[:-1, 1]  # drop perfectly conducting core

        periods = np.logspace(np.log10(1/48), np.log10(365*24))*3600

        C_n, rho_a, phi, Q_n = c.conducting_sphere(periods, sigma, radius, n,
                                                   kind='thick')

        self.assertIsNone(np.testing.assert_allclose(C_n, C_n_mat))
        self.assertIsNone(np.testing.assert_allclose(rho_a, rho_a_mat))
        self.assertIsNone(np.testing.assert_allclose(phi, phi_mat))
        self.assertIsNone(np.testing.assert_allclose(Q_n, Q_n_mat))

    def test_q_response_sphere(self):

        a = 6371.2
        n = 1

        # load matfile
        test = load_matfile(MATFILE_PATH, 'test_conducting_sphere_thinlayer')

        C_n_mat = np.ravel(test['C_n'])
        rho_a_mat = np.ravel(test['rho_a'])
        phi_mat = np.ravel(test['phi'])
        Q_n_mat = np.ravel(test['Q_n'])

        model = np.loadtxt('/home/ancklo/Documents/Python/' +
                           'Chaos-master/data/conductivity_Grayver2017.dat')

        radius = a - model[:, 0]
        sigma = model[:, 1]

        periods = np.logspace(np.log10(1/48), np.log10(365*24))*3600

        C_n, rho_a, phi, Q_n = c.q_response_sphere(
            periods, sigma, radius, n, kind='thin')

        self.assertIsNone(np.testing.assert_allclose(C_n, C_n_mat))
        self.assertIsNone(np.testing.assert_allclose(rho_a, rho_a_mat))
        self.assertIsNone(np.testing.assert_allclose(phi, phi_mat))
        self.assertIsNone(np.testing.assert_allclose(Q_n, Q_n_mat))

    def test_synth_rotate_gauss(self):
        """
        Tests the accuracy of the Fourier representation of tranformation
        matrices by comparing them with directly computed matrices (they are
        considered correct).

        """

        for reference in ['gsm', 'sm']:

            print(f'  Testing {reference.upper()} frame of reference.')

            # load spectrum to synthesize matrices in time-domain
            filepath = c.basicConfig[f'file.{reference.upper()}_spectrum']

            try:
                data = np.load(filepath)
            except FileNotFoundError as e:
                raise ValueError(
                    'Reference file "frequency_spectrum_{reference}.npz"'
                    ' not found in "chaosmagpy/lib/".'
                    ' Correct reference?') from e

            frequency = data['frequency']  # oscillations per day
            spectrum = data['spectrum']

            print("  Testing 50 times within 1996 and 2024.")
            for time in np.linspace(-4*365.25, 24*365.25, 50):

                matrix_time = c.synth_rotate_gauss(
                    time, frequency, spectrum, scaled=True)

                nmax = int(np.sqrt(spectrum.shape[1] + 1) - 1)
                kmax = int(np.sqrt(spectrum.shape[2] + 1) - 1)

                if reference == 'gsm':
                    base_1, base_2, base_3 = c.basevectors_gsm(time)
                elif reference == 'sm':
                    base_1, base_2, base_3 = c.basevectors_sm(time)

                matrix = c.rotate_gauss(nmax, kmax, base_1, base_2, base_3)

                stat = np.amax(np.abs(matrix-np.squeeze(matrix_time)))
                print('  Computed year {:4.2f}, '
                      'max. abs. error = {:.3e}'.format(
                          time/365.25 + 2000, stat), end='')
                if stat > 0.001:
                    print(' ' + min(int(stat/0.001), 10) * '*')
                else:
                    print('')

                self.assertIsNone(np.testing.assert_allclose(
                    matrix, np.squeeze(matrix_time), rtol=1e-1, atol=1e-1))

    def test_rotate_gauss_fft(self):

        nmax = 2
        kmax = 2

        # load matfile
        test = load_matfile(MATFILE_PATH, 'test_rotate_gauss_fft')

        for reference in ['gsm', 'sm']:

            frequency, amplitude, _, _ = c.rotate_gauss_fft(
                nmax, kmax, step=1., N=int(365*24), filter=20, save_to=False,
                reference=reference, scaled=False)

            omega = 2*pi*frequency / (24*3600)

            # transpose and take complex conjugate (to match original output)
            omega_mat = \
                test['omega_{:}'.format(reference)].transpose((2, 1, 0))
            amplitude_mat = \
                test['amplitude_{:}'.format(reference)].transpose((2, 1, 0))
            amplitude_mat = amplitude_mat.conj()

            # absolute tolerance to account for close-to-zero matrix entries
            self.assertIsNone(np.testing.assert_allclose(
                omega_mat, omega, atol=1e-3))
            self.assertIsNone(np.testing.assert_allclose(
                amplitude_mat, amplitude, atol=1e-3))

    def test_rotate_gauss(self):

        # test 1
        time = 20  # random day
        nmax = 4
        kmax = 2

        s = timer()

        base_1, base_2, base_3 = c.basevectors_gsm(time)
        matrix = c.rotate_gauss(nmax, kmax, base_1, base_2, base_3)

        e = timer()

        # load matfile
        test = load_matfile(MATFILE_PATH, 'test_rotate_gauss')

        matrix_mat = test['m_all'].transpose()  # transposed in Matlab code
        runtime = test['runtime']

        print("  Time for matrix computation (Python): ", e - s)
        print("  Time for matrix computation (Matlab):  {:}".format(
            runtime[0, 0]))

        # absolute tolerance to account for close-to-zero matrix entries
        self.assertIsNone(np.testing.assert_allclose(
            matrix, matrix_mat, atol=1e-8))

        # test 2
        # rotate around y-axis to have dipole axis aligned with x-axis
        base_1 = np.array([0, 0, -1])
        base_2 = np.array([0, 1, 0])
        base_3 = np.array([1, 0, 0])

        nmax = 1  # only dipole terms
        kmax = 1

        matrix = c.rotate_gauss(nmax, kmax, base_1, base_2, base_3)
        desired = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])

        self.assertIsNone(np.testing.assert_allclose(
            matrix, desired, atol=1e-10))

        # test 3
        time = np.arange(9).reshape((3, 3))  # random day
        nmax = 4
        kmax = 2

        base_1, base_2, base_3 = c.basevectors_gsm(time)
        matrix = c.rotate_gauss(nmax, kmax, base_1, base_2, base_3)

        self.assertEqual(matrix.shape, (3, 3, 24, 8))

    def test_cartesian_to_spherical(self):

        x = -1.0
        y = 0.0
        z = 0.0

        radius = 1.0
        theta = 90.
        phi = 180.

        result = (radius, theta, phi)
        self.assertAlmostEqual(c.cartesian_to_spherical(x, y, z), result)

    def test_spherical_to_cartesian(self):

        radius = 1.
        theta = pi/2
        phi = pi

        x = np.array(radius) * np.sin(theta) * np.cos(phi)
        y = np.array(radius) * np.sin(theta) * np.sin(phi)
        z = np.array(radius) * np.cos(theta)

        result = (x, y, z)

        theta, phi = np.degrees(theta), np.degrees(phi)

        self.assertEqual(c.spherical_to_cartesian(radius, theta, phi), result)
        self.assertEqual(c.spherical_to_cartesian(1, theta, phi), result)
        self.assertEqual(c.spherical_to_cartesian(
            theta=theta, radius=radius, phi=phi), result)
        self.assertEqual(c.spherical_to_cartesian(
            radius=1, phi=phi, theta=theta), result)

    def test_matrix_geo_to_base(self):

        theta_geo = np.linspace(1, 179, 10)
        phi_geo = np.linspace(-179, 179, 10)
        time = np.linspace(-300, 10000, 10)

        for reference in ['sm', 'gsm', 'mag']:
            print(f'  Testing {reference.upper()}')

            if reference == 'mag':
                base_1, base_2, base_3 = c.basevectors_mag()
            elif reference == 'sm':
                base_1, base_2, base_3 = c.basevectors_sm(time)
            elif reference == 'gsm':
                base_1, base_2, base_3 = c.basevectors_gsm(time)

            theta_ref, phi_ref, R = c.matrix_geo_to_base(
                theta_geo, phi_geo, base_1, base_2, base_3, inverse=False)

            theta_geo2, phi_geo2, R2 = c.matrix_geo_to_base(
                theta_ref, phi_ref, base_1, base_2, base_3, inverse=True)

            self.assertIsNone(
                np.testing.assert_allclose(theta_geo, theta_geo2))
            self.assertIsNone(
                np.testing.assert_allclose(phi_geo, phi_geo2))

            R_full = np.matmul(R, R2)
            R_full2 = np.zeros((theta_geo.size, 3, 3))
            for n in range(3):
                R_full2[..., n, n] = 1.

            self.assertIsNone(
                np.testing.assert_allclose(R_full, R_full2, atol=1e-7))

    def test_geo_to_sm(self):

        time = np.linspace(1, 100, 10)
        theta_geo = np.linspace(1, 179, 10)
        phi_geo = np.linspace(-180, 179, 10)

        # load matfile
        test = load_matfile(MATFILE_PATH, 'test_geo_to_sm')

        # reduce 2-D matrix to 1-D vectors
        theta_sm_mat = np.ravel(test['theta_sm'])
        phi_sm_mat = np.ravel(test['phi_sm'])

        theta_sm, phi_sm = c.transform_points(theta_geo, phi_geo,
                                              time=time, reference='sm')

        self.assertIsNone(np.testing.assert_allclose(theta_sm, theta_sm_mat))
        self.assertIsNone(np.testing.assert_allclose(phi_sm, phi_sm_mat))

    def test_geo_to_gsm(self):

        time = np.linspace(1, 100, 10)
        theta_geo = np.linspace(1, 179, 10)
        phi_geo = np.linspace(-180, 179, 10)

        # load matfile
        test = load_matfile(MATFILE_PATH, 'test_geo_to_gsm')

        # reduce 2-D matrix to 1-D vectors
        theta_gsm_mat = np.ravel(test['theta_gsm'])
        phi_gsm_mat = np.ravel(test['phi_gsm'])

        theta_gsm, phi_gsm = c.transform_points(
            theta_geo, phi_geo, time=time, reference='gsm')

        self.assertIsNone(np.testing.assert_allclose(theta_gsm, theta_gsm_mat))
        self.assertIsNone(np.testing.assert_allclose(phi_gsm, phi_gsm_mat))

    def test_geo_to_base(self):

        time = np.linspace(1, 100, 10)
        theta_geo = np.linspace(1, 179, 10)
        phi_geo = np.linspace(-180, 179, 10)

        # TEST GSM COORDINATES
        # GSM test: load matfile
        test = load_matfile(MATFILE_PATH, 'test_geo_to_gsm')

        # reduce 2-D matrix to 1-D vectors
        theta_gsm_mat = np.ravel(test['theta_gsm'])
        phi_gsm_mat = np.ravel(test['phi_gsm'])

        gsm_1, gsm_2, gsm_3 = c.basevectors_gsm(time)

        theta_gsm, phi_gsm = c.geo_to_base(
            theta_geo, phi_geo, gsm_1, gsm_2, gsm_3)

        self.assertIsNone(np.testing.assert_allclose(theta_gsm, theta_gsm_mat))
        self.assertIsNone(np.testing.assert_allclose(phi_gsm, phi_gsm_mat))

        # test the inverse option: GEO -> GSM -> GEO
        theta_geo2, phi_geo2 = c.geo_to_base(
            theta_gsm, phi_gsm, gsm_1, gsm_2, gsm_3, inverse=True)

        self.assertIsNone(np.testing.assert_allclose(theta_geo, theta_geo2))
        self.assertIsNone(np.testing.assert_allclose(
            phi_geo, c.center_azimuth(phi_geo2)))

        # test the inverse option: GSM -> GEO -> GSM
        theta_gsm2, phi_gsm2 = c.geo_to_base(
            theta_geo2, phi_geo2, gsm_1, gsm_2, gsm_3)

        self.assertIsNone(np.testing.assert_allclose(theta_gsm, theta_gsm2))
        self.assertIsNone(np.testing.assert_allclose(
            c.center_azimuth(phi_gsm), c.center_azimuth(phi_gsm2)))

        # TEST SM COORDINATES
        # SM test: load matfile
        test = load_matfile(MATFILE_PATH, 'test_geo_to_sm')

        # reduce 2-D matrix to 1-D vectors
        theta_sm_mat = np.ravel(test['theta_sm'])
        phi_sm_mat = np.ravel(test['phi_sm'])

        sm_1, sm_2, sm_3 = c.basevectors_sm(time)

        theta_sm, phi_sm = c.geo_to_base(
            theta_geo, phi_geo, sm_1, sm_2, sm_3)

        self.assertIsNone(np.testing.assert_allclose(theta_sm, theta_sm_mat))
        self.assertIsNone(np.testing.assert_allclose(phi_sm, phi_sm_mat))

        # test the inverse option: GEO -> SM -> GEO
        theta_geo2, phi_geo2 = c.geo_to_base(
            theta_sm, phi_sm, sm_1, sm_2, sm_3, inverse=True)

        self.assertIsNone(np.testing.assert_allclose(theta_geo, theta_geo2))
        self.assertIsNone(np.testing.assert_allclose(phi_geo, phi_geo2))

        # test the inverse option: SM -> GEO -> SM
        theta_sm2, phi_sm2 = c.geo_to_base(
            theta_geo2, phi_geo2, sm_1, sm_2, sm_3)

        self.assertIsNone(np.testing.assert_allclose(theta_sm, theta_sm2))
        self.assertIsNone(np.testing.assert_allclose(phi_sm, phi_sm2))

    def test_basevectors_use(self):

        # test local transformation at specific point
        R = np.stack(c.basevectors_use(
            theta=90., phi=180.), axis=-1)
        desired = np.array([[-1, 0, 0], [0, 0, -1], [0, -1, 0]])

        self.assertIsNone(np.testing.assert_allclose(R, desired, atol=1e-10))

        # test local transformation at specific point
        R = np.stack(c.basevectors_use(
            theta=90., phi=-90.), axis=-1)
        desired = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]])

        self.assertIsNone(np.testing.assert_allclose(R, desired, atol=1e-10))

    def test_sun_position(self):

        start = d.mjd2000(1910, 1, 1)
        end = d.mjd2000(2090, 12, 31)
        time = np.linspace(start, end, 100)

        theta, phi = c.sun_position(time)

        # load matfile
        test = load_matfile(MATFILE_PATH, 'test_sun_position')

        # reduce 2-D matrix to 1-D vectors
        theta_mat = np.ravel(test['theta'])
        phi_mat = np.ravel(test['phi'])

        self.assertIsNone(np.testing.assert_allclose(theta, theta_mat))
        self.assertIsNone(np.testing.assert_allclose(phi, phi_mat))

        # test position of sun close to zenith in Greenwich
        # (lat 51.48, lon -0.0077) on July 18, 2018, 12h06 (from
        # sunearthtools.com):

        time_gmt = d.mjd2000(2018, 7, 18, 12, 6)
        lat = 51.4825766  # geogr. latitude
        lon = -0.0076589  # geogr. longitude
        el = 59.59  # elevation above horizon
        az = 179.86  # angle measured from north (sun close to zenith)

        theta_gmt = 180. - (el + lat)  # subsolar colat. given geogr. lat.
        phi_gmt = 180. + (lon - az)  # subsolar phi given geogr. longitude

        theta, phi = c.sun_position(time_gmt)

        self.assertAlmostEqual(theta_gmt, theta, places=0)
        self.assertAlmostEqual(phi_gmt, phi, places=0)

    def test_center_azimuth(self):

        angle = 180.

        self.assertAlmostEqual(c.center_azimuth(0.25*angle), 0.25*angle)
        self.assertAlmostEqual(c.center_azimuth(0.75*angle), 0.75*angle)
        self.assertAlmostEqual(c.center_azimuth(1.25*angle), -0.75*angle)
        self.assertAlmostEqual(c.center_azimuth(1.75*angle), -0.25*angle)
        self.assertAlmostEqual(c.center_azimuth(-0.25*angle), -0.25*angle)
        self.assertAlmostEqual(c.center_azimuth(-0.75*angle), -0.75*angle)
        self.assertAlmostEqual(c.center_azimuth(-1.25*angle), 0.75*angle)
        self.assertAlmostEqual(c.center_azimuth(-1.75*angle), 0.25*angle)


if __name__ == '__main__':
    main()
