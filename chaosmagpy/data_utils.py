import pandas as pd
import numpy as np
import os


def load_RC_datfile(filepath, parse_dates=False):
    """
    Load RC-index data file into pandas data frame.

    Parameters
    ----------
    filepath : str
        File path to RC-index dat-file.
    parse_dates : bool, optional
        Replace index with datetime object for time-series manipulations.
        Default is ``False``.

    Returns
    -------
    df : dataframe
        Pandas dataframe with names {'time', 'RC', 'RC_e', 'RC_i', 'flag'},
        where ``'time'`` is given in modified Julian dates.

    """

    column_names = ['time', 'RC', 'RC_e', 'RC_i', 'flag']
    column_types = {'time': 'float64', 'RC': 'float64', 'RC_e': 'float64',
                    'RC_i': 'float64', 'flag': 'category'}

    df = pd.read_csv(str(filepath),  delim_whitespace=True, comment='#',
                     dtype=column_types, names=column_names)

    # set datetime as index
    if parse_dates is True:
        df.index = pd.to_datetime(
            df['time'].values, unit='D', origin=pd.Timestamp('2000-1-1'))
        df.drop(['time'], axis=1, inplace=True)  # delete redundant time column

    return df


def load_shcfile(filepath):
    """
    Load shc-file and return coefficient arrays.

    Parameters
    ----------
    filepath : str
        File path to spherical harmonic coefficient shc-file.

    Returns
    -------
    time : ndarray, shape (N,)
        Array containing `N` times for each model snapshot in modified
        Julian dates with origin January 1, 2000 0:00 UTC.
    coeffs : ndarray, shape (nmax(nmax+2), N)
        Coefficients of model snapshots. Each column is a snapshot up to
        spherical degree and order `nmax`.
    parameters : dict, {'SHC', 'nmin', 'nmax', 'N', 'order', 'step'}
        Dictionary containing parameters of the model snapshots and the
        following keys: ``'SHC'`` shc-file name, `nmin` minimum degree,
        ``'nmax'`` maximum degree, ``'N'`` number of snapshot models,
        ``'order'`` piecewise polynomial order and ``'step'`` number of
        snapshots until next break point. Extract break points of the
        piecewise polynomial with ``breaks = time[::step]``.

    """

    with open(filepath, 'r') as f:

        data = np.array([])
        for line in f.readlines():

            if line[0] == '#':
                continue

            read_line = np.fromstring(line, sep=' ')
            if read_line.size == 5:
                name = os.path.split(filepath)[1]  # file name string
                values = [name] + read_line.astype(np.int).tolist()

            else:
                data = np.append(data, read_line)

        # unpack parameter line
        keys = ['SHC', 'nmin', 'nmax', 'N', 'order', 'step']
        parameters = dict(zip(keys, values))

        time = data[:parameters['N']]
        coeffs = data[parameters['N']:].reshape((-1, parameters['N']+2))
        coeffs = np.squeeze(coeffs[:, 2:])  # discard columns with n and m

    return (time - 2000.) * 365.25, coeffs, parameters


def load_magfile(filepath, parse_dates=False):

    column_names = ['theta', 'phi', 'time', 'radius', 'B_radius',
                    'B_theta', 'B_phi', 'codes']

    # convert decimal years to mjd2000
    def to_mjd2000(time):
        time = float(time)
        if time == 99999:
            return np.nan
        else:
            return (time - 2000.) * 365.25

    df = pd.read_csv(str(filepath),  delim_whitespace=True, comment='%',
                     names=column_names, na_values=99999,
                     usecols=column_names, converters={'time': to_mjd2000})

    # reordered column names to get "natural" ordering
    column_names = ['time', 'radius', 'theta', 'phi', 'B_radius',
                    'B_theta', 'B_phi', 'codes']
    df = df.reindex(columns=column_names)

    # set datetime as index
    if parse_dates is True:
        df.index = pd.to_datetime(
            df['time'].values, unit='D', origin=pd.Timestamp('2000-1-1'))
        df.drop(['time'], axis=1, inplace=True)  # delete redundant time column

    return df


def memory_usage(pandas_obj):
    """
    Compute memory usage of pandas object. For full report, use:
    ``df.info(memory_usage='deep')``.

    """

    if isinstance(pandas_obj, pd.DataFrame):
        usage_b = pandas_obj.memory_usage(deep=True).sum()
    else:  # we assume if not a df it's a series
        usage_b = pandas_obj.memory_usage(deep=True)
    usage_mb = usage_b / 1024 ** 2  # convert bytes to megabytes
    return "{:03.2f} MB".format(usage_mb)


def gauss_units(deriv):
    """
    Return string of the magnetic field units given the derivative with time.
    String is meant to be parsed to plot labels.
    """

    if deriv == 0:
        units = 'nT'
    else:
        units = '$\mathrm{{nT}}\cdot \mathrm{{yr}}^{{{:}}}$'.format(-deriv)

    return units


def rsme(x, y):
    """
    Compute RSME (root square mean error) of inputs x and y.

    Parameters
    ----------
    x, y : ndarray
    """

    x = np.array(x)
    y = np.array(y)

    return np.mean(np.abs(x-y)**2)**0.5
