import sys
from pathlib import Path
from functools import partial
import warnings
import numpy as np
import pandas as pd
from . import merge
from ..error_handling import permission_popup, except_none_log
from ..filefuncs import archive

@except_none_log
def get_test_specs_df(merged_df, paths, report_type):
    """Create a dataframe from test-metadata.csv and test data which displays the test specifics."""
    # todo: get don't use test metadata for PCL testing
    if report_type == 'pcl':
        test_specs_df = pd.read_excel(paths['entry_forms'], sheet_name='Misc', header=None, index_col=0)
    else:
        test_specs_df = pd.read_csv(paths['test_metadata'], header=None, index_col=0)
    test_specs_df.columns = [0]

    start_date = pd.to_datetime(merged_df['time']).min().date()
    start_time = pd.to_datetime(merged_df['time']).min().time()
    end_time = pd.to_datetime(merged_df['time']).max().time()
    duration = pd.to_datetime(merged_df['time']).max() - pd.to_datetime(merged_df['time']).min()
    data = {
        'Test Start Date': start_date,
        'Test Start Time': start_time,
        'Test End Time': end_time,
        'Test Duration': duration
    }

    beginning_rows = pd.DataFrame.from_dict(data, orient='index')
    test_specs_df = pd.concat([beginning_rows, test_specs_df])

    return test_specs_df

@except_none_log
@permission_popup
def get_results_summary_df(merged_df, data_folder, waketimes):
    """Create a dataframe with one line per test showing test info and test results (average watts and nits)."""
    rsdf = merged_df.groupby(['tag']).first()

    cols = ['test_name', 'test_time', 'preset_picture', 'video', 'mdd', 'abc', 'lux', 'qs']
    cols = [col for col in cols if col in rsdf.columns]
    rsdf = rsdf[cols]
    avg_cols = ['watts', 'nits', "APL'"]
    rsdf = pd.concat([rsdf, merged_df.groupby(['tag']).mean()[avg_cols]], axis=1)
    rsdf['waketime'] = rsdf['test_name'].apply(waketimes.get)

    for i, row in rsdf.reset_index().iterrows():
        if 'standby' in row['test_name']:
            # todo: handle standby test not being long enough
            if len(merged_df) > (20*60):
                last20_df = merged_df[merged_df['tag'] == row['tag']].iloc[-20 * 60:]
                for col in ['watts', 'nits']:
                    rsdf.loc[row['tag'], col] = last20_df[col].mean()

    rsdf.to_csv(Path(data_folder).joinpath('results-summary.csv'))
    return rsdf

@except_none_log
def get_waketimes(merged_df):
    """Calculate wake times from the test data and return as a dictionary."""
    return dict(zip(merged_df['test_name'], merged_df['waketime']))

@except_none_log
def get_on_mode_df(rsdf, limit_funcs, area, report_type):
    """Create a dataframe and corresponding reportlab TableStyle data which displays the results of on mode testing."""
    def add_pps_tests(on_mode_df, cdf, abc_off_test, abc_on_tests, limit_func):
        on_mode_df = on_mode_df.append(cdf.loc[abc_off_test])

        abc_off_pwr = on_mode_df.loc[abc_off_test, 'watts']
        abc_off_lum = on_mode_df.loc[abc_off_test, 'nits']
        if abc_on_tests:
            for test in abc_on_tests:
                on_mode_df = on_mode_df.append(cdf.loc[test])
            abc_on_pwr = on_mode_df.loc[abc_on_tests, 'watts'].mean()
            abc_on_lum = on_mode_df.loc[abc_on_tests, 'nits'].mean()
            measured = {
                'nits': np.mean([abc_on_lum, abc_off_lum]),
                'watts': np.mean([abc_on_pwr, abc_off_pwr])
            }
        else:
            measured = {
                'nits': np.mean(abc_off_lum),
                'watts': np.mean(abc_off_pwr)
            }
        measured_name = f'{abc_off_test}_measured'
        on_mode_df = on_mode_df.append(pd.Series(data=measured, name=measured_name))
        limit = limit_func(area=area, luminance=on_mode_df.loc[measured_name, 'nits'])
        on_mode_df.loc[measured_name, 'limit'] = limit
        return on_mode_df

    cdf = rsdf.set_index('test_name')
    on_mode_df = cdf.drop(cdf.index)

    def_abc_tests = [test for test in ['default_100', 'default_35', 'default_12', 'default_3'] if test in cdf.index]
    on_mode_df = add_pps_tests(on_mode_df, cdf, 'default', def_abc_tests, limit_funcs['default'])

    br_abc_tests = [test for test in ['brightest_100', 'brightest_35', 'brightest_12', 'brightest_3'] if
                    test in cdf.index]
    on_mode_df = add_pps_tests(on_mode_df, cdf, 'brightest', br_abc_tests, limit_funcs['brightest'])
    
    # todo: implement hdr arg instead of this
    if 'hdr' in cdf.index:
        hdr_abc_tests = [test for test in ['hdr_100', 'hdr_35', 'hdr_12', 'hdr_3'] if test in cdf.index]
        on_mode_df = add_pps_tests(on_mode_df, cdf, 'hdr', hdr_abc_tests, limit_funcs['hdr'])

    on_mode_df = on_mode_df.reset_index()
    on_mode_df['ratio'] = on_mode_df['watts']/on_mode_df['limit']
    if report_type == 'estar':
        s = f"{sum(on_mode_df['ratio'].dropna() < 1)}/{len(on_mode_df['ratio'].dropna())}"
        data = {'test_name': 'passing_pps', 'ratio': s}
    else:
        data = {'test_name': 'average_measured', 'ratio': on_mode_df['ratio'].mean()}
    on_mode_df = on_mode_df.append(data, ignore_index=True)
    
    cols = ['test_name', 'preset_picture', 'abc', 'lux', 'mdd', 'nits', 'limit', 'watts', 'ratio']
    cols = [col for col in cols if col in on_mode_df.columns]
    on_mode_df = on_mode_df[cols]
    return on_mode_df

@except_none_log
def get_standby_df(rsdf):
    """Create a dataframe and corresponding reportlab TableStyle data which displays the results of standby testing."""
    standby_df = rsdf[rsdf['test_name'].apply(lambda x: 'standby' in x)].copy()
    standby_df['limit'] = 2
    cols = ['test_name', 'qs', 'waketime', 'limit', 'watts']
    cols = [col for col in cols if col in standby_df.columns]
    standby_df = standby_df.reset_index()[cols]

    return standby_df

@except_none_log
def get_persistence_dfs(paths):
    df = pd.read_excel(paths['entry_forms'], sheet_name='Persistence Summary')
    persistence_dfs = {}
    for mode in ['SDR', 'HDR 10', 'HLG', 'Dolby Vision']:
        start_idx = [i for i, col in enumerate(df.columns) if mode in col][0]
        end_idx = start_idx + 3
        mode_df = df.iloc[:, start_idx:end_idx]
        mode_df.columns = mode_df.iloc[0]
        mode_df.drop(df.index[0], inplace=True)
        persistence_dfs[mode.lower().replace(' ', '_')] = mode_df.dropna(subset=['Preset Picture Setting'])
    return persistence_dfs

@except_none_log
def get_report_type(docopt_args, data_folder):
    if docopt_args['-e'] or 'ENERGYSTAR' in data_folder.stem:
        return 'estar'
    elif docopt_args['-v'] or 'Alternative' in data_folder.stem:
        return 'alternative'
    elif docopt_args['-p'] or 'PCL' in data_folder.stem:
        return 'pcl'
    else:
        warnings.warn('Report type could not be identified. Attempting ENERGYSTAR report...')
        return 'estar'
    return report_type

@except_none_log
def power_cap_funcs():
    def power_cap(area, sf, a, b):
        return sf * ((a * area) + b)
    power_cap_coeffs = pd.read_csv(Path(sys.path[0]).joinpath(r'config\power-cap-coeffs.csv'), index_col='coef').to_dict()
    power_cap_funcs = {func_name: partial(power_cap, **coeff_vals) for func_name, coeff_vals in
                       power_cap_coeffs.items()}
    return power_cap_funcs

@except_none_log
def get_limit_funcs(report_type):
    def power_limit(area, luminance, sf, a, b, c, d, e, f, power_cap_func=None):
        limit = sf * ((a * area + b) * (e * luminance + f) + c * area + d)
        if power_cap_func is not None:
            return min(limit, power_cap_func(area))
        else:
            return limit
    
    coeffs = pd.read_csv(Path(sys.path[0]).joinpath(r'config\coeffs.csv'), index_col='coef').to_dict()
    if report_type == 'estar':
        for func_name in coeffs:
            coeffs[func_name]['power_cap_func'] = power_cap_funcs()[func_name]

    limit_funcs = {func_name: partial(power_limit, **coeff_vals) for func_name, coeff_vals in coeffs.items()}
    return limit_funcs

@except_none_log
@permission_popup
def get_merged_df(paths, data_folder):
    test_seq_df = pd.read_csv(paths['test_seq'])
    data_df = pd.read_csv(paths['test_data'], parse_dates=['Timestamp'])
    archive(paths['test_data'])
    merged_df = merge.merge_test_data(test_seq_df, data_df)
    merged_df['source'] = Path(paths['test_data']).name
    
    if paths['old_merged'] is not None:
        old_merged_df = pd.read_csv(paths['old_merged'])
        archive(paths['old_merged'])
        old_merged_df = old_merged_df.append({'test_name':-1}, ignore_index=True)
        merged_df = pd.concat([old_merged_df, merged_df]).reset_index()[merged_df.columns]
        merged_df = merge.remove_rows_rewind(merged_df, col='test_name')
        merged_df = merged_df.query('test_name!=-1')
        
        
    merged_df.to_csv(Path(data_folder).joinpath('merged.csv'), index=False)
    
    # todo: handle different report types
    
    return merged_df

@except_none_log
def get_spectral_df(paths):
    df = pd.read_csv(paths['spectral_profile']).iloc[39:]
    df = df.astype(float).set_index(df.columns[0])
    df.index.name = 'Wavelength (nm)'
    return df

@except_none_log
def get_lum_df(paths):
    return pd.read_csv(paths['lum_profile'], header=None)


def get_ccf_df(merged_df, data_folder):
    ccf_df = pd.DataFrame(columns=['test_name', 'grey1', 'grey2', 'grey3', 'grey4', 'grey5'])
    manual_ccf_tests = [test_name for test_name in merged_df.test_name.unique() if 'manual_ccf' in test_name]
    for test_name in manual_ccf_tests:
        tdf = merged_df.query('test_name==@test_name').copy()
        row = {f'grey{i + 1}': tdf['nits'].iloc[i * 40 + 19:i * 40 + 24].mean() for i in range(len(tdf) // 40)}
        row['test_name'] = test_name
        ccf_df = ccf_df.append(row, ignore_index=True)
    
    path = Path(data_folder).joinpath('ccf-summary.csv')
    ccf_df.to_csv(path, index=False)

@except_none_log
def get_hdr(merged_df):
    return 'hdr10' in merged_df.test_name.unique() or 'hdr' in merged_df.test_name.unique()

@except_none_log
def get_test_date(test_specs_df):
    return pd.to_datetime(test_specs_df.loc['Test Start Date', 0]).date().strftime('%d-%b-%Y')

@except_none_log
def get_screen_area(test_specs_df):
    return float(test_specs_df.loc['Screen Area (sq in)', 0])

@except_none_log
def get_model(test_specs_df):
    return f"{str(test_specs_df.loc['Make', 0]).upper()} {str(test_specs_df.loc['Model', 0]).upper()}"


def get_report_data(paths, data_folder, docopt_args):
    data = {}
    data['data_folder'] = data_folder
    data['report_type'] = get_report_type(docopt_args, data_folder)
    data['merged_df'] = get_merged_df(paths, data_folder)
    data['hdr'] = get_hdr(data['merged_df'])
    data['limit_funcs'] = get_limit_funcs(data['report_type'])
    if data['report_type']=='pcl':
        data['persistence_dfs'] = get_persistence_dfs(paths)
        data['spectral_df'] = get_spectral_df(paths)
    else:
        data['persistence_dfs'] = None
        data['spectral_df'] = None
    data['waketimes'] = get_waketimes(data['merged_df'])
    data['rsdf'] = get_results_summary_df(data['merged_df'], data_folder, data['waketimes'])
    data['test_specs_df'] = get_test_specs_df(data['merged_df'], paths, data['report_type'])
    data['test_date'] = get_test_date(data['test_specs_df'])
    data['area'] = get_screen_area(data['test_specs_df'])
    data['model'] = get_model(data['test_specs_df'])
    
    data['on_mode_df'] = get_on_mode_df(data['rsdf'], data['limit_funcs'], data['area'], data['report_type'])
    data['standby_df'] = get_standby_df(data['rsdf'])
    data['lum_df'] = get_lum_df(paths)
    return data


def check_report_data(report_data, expected_data):
    data_items = {
        'report_type': 'report type',
        'merged_df': 'merged time series data (merged.csv)',
        'hdr': 'hdr capability',
        'limit_funcs': 'power limit equations',
        'persistence_dfs': 'ABC/MDD persistence tables',
        'spectral_df': 'spectral distribution data',
        'waketimes': 'standby waketimes',
        'rsdf': 'results summary table',
        'test_specs_df': 'test specifics table',
        'test_date': 'date of testing',
        'area': 'screen area',
        'model': 'television model number',
        'on_mode_df': 'on mode compliance table',
        'standby_df': 'standby compliance table',
        'lum_df': 'luminance profile'
    }
    warnings.filterwarnings('always', category=UserWarning)
    for item in expected_data:
        if item not in report_data.keys():
            msg = f'\nMissing Data Item:\n\tCould not construct/identify {data_items.get(item, "**unknown data item**")}\n\nReport may be incomplete.'
            warnings.warn(msg)