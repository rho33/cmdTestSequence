import sys
import os
import random
import shutil
from collections import defaultdict
from pathlib import Path
from functools import partial
import warnings
import numpy as np
import pandas as pd
from scipy.stats import linregress
from colour.models import BT2020_COLOURSPACE, BT709_COLOURSPACE
from colour import XYZ_to_Lab, Lab_to_LCHab
from . import merge
from ..error_handling import permission_popup, except_none_log
from ..filefuncs import archive

@except_none_log
def get_test_specs_df(merged_df, paths, report_type, clean=False):
    """Create a dataframe from test-metadata.csv and test data which displays the test specifics."""
    if report_type == 'pcl' and paths['entry_forms'] is not None:
        test_specs_df = pd.read_excel(paths['entry_forms'], sheet_name='Misc', header=None, index_col=0)
        test_specs_df.columns = [0]
    else:
        test_specs_df = pd.read_csv(paths['test_metadata'], encoding='iso-8859-1', header=None, index_col=0)
        test_specs_df.columns = [0]
        if 'Screen Area (sq in)' not in test_specs_df.index:
            height_idx_loc = list(test_specs_df.index).index('Screen Height')
            df1 = test_specs_df[:height_idx_loc+1]
            area = float(test_specs_df.loc['Screen Width', 0]) * float(test_specs_df.loc['Screen Height', 0])
            df1.loc['Screen Area (sq in)'] = area
            df2 = test_specs_df.iloc[height_idx_loc + 1:]
            test_specs_df = pd.concat([df1, df2])

        d = {'TV Make': 'Make', 'TV Model': 'Model'}

        test_specs_df.index = test_specs_df.index.to_series().replace(d).values
        if clean:
            if 'Make' in test_specs_df.index:
                test_specs_df.loc['Make', 0] = 'XXXXX'
            if 'Model' in test_specs_df.index:
                test_specs_df.loc['Model', 0] = 'XXXXX'
            if 'Serial Number' in test_specs_df.index:
                test_specs_df.loc['Serial Number', 0] = 'XXXXX'

        

    # start_date = pd.to_datetime(merged_df['time']).min().date()
    # start_time = pd.to_datetime(merged_df['time']).min().time()
    # end_time = pd.to_datetime(merged_df['time']).max().time()
    # duration = pd.to_datetime(merged_df['time']).max() - pd.to_datetime(merged_df['time']).min()
    # data = {
    #     'Test Start Date': start_date,
    #     'Test Start Time': start_time,
    #     'Test End Time': end_time,
    #     'Test Duration': duration
    # }
    #
    # beginning_rows = pd.DataFrame.from_dict(data, orient='index')
    # test_specs_df = pd.concat([beginning_rows, test_specs_df])

    return test_specs_df

@except_none_log
@permission_popup
def get_results_summary_df(merged_df, data_folder, waketimes):
    """Create a dataframe with one line per test showing test info and test results (average watts and nits)."""
    rsdf = merged_df.groupby(['tag']).first()

    cols = ['test_name', 'test_time', 'preset_picture', 'video', 'abc', 'lux', 'qs']
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
def get_compliance_summary_df(on_mode_df, standby_df, report_type, hdr):
    
    if report_type == 'estar':
        cols = ['test_name', 'watts', 'limit', 'result']
        csdf = pd.concat([on_mode_df[cols], standby_df[cols]])

    else:
        pps_list = ['default', 'brightest', 'hdr10'] if hdr else ['default_brightest']
        test_names = [f'{pps}_measured' if f'{pps}_measured' in on_mode_df['test_name'].values else pps for pps in pps_list]
        test_names.append('average_measured')
        mask = on_mode_df['test_name'].apply(lambda test_name: test_name in test_names)
        cols = ['test_name', 'watts', 'limit']
        csdf = pd.concat([on_mode_df[mask], standby_df])[cols]
        csdf['result'] = (csdf['watts'] < csdf['limit']).apply({True: 'Pass', False: 'Fail'}.get)
        idx = on_mode_df[on_mode_df['test_name'] == 'average_measured'].index[0]
        avg_ratio = on_mode_df.loc[idx, 'ratio']
        idx = csdf[csdf['test_name'] == 'average_measured'].index[0]
        csdf.loc[idx, 'result'] = 'Pass' if avg_ratio < 1 else 'Fail'
        
    return csdf.reset_index().drop('index', axis=1)

@except_none_log
def get_on_mode_df(rsdf, limit_funcs, area, limit_type, hdr):
    """Create a dataframe and corresponding reportlab TableStyle data which displays the results of on mode testing."""
    def add_pps_tests(on_mode_df, cdf, abc_off_test, abc_on_tests, limit_func):
        on_mode_df = on_mode_df.append(cdf.loc[abc_off_test])

        abc_off_pwr = on_mode_df.loc[abc_off_test, 'watts']
        abc_off_lum = on_mode_df.loc[abc_off_test, 'nits']
        if abc_on_tests and limit_type != 'estar':
            for test in abc_on_tests:
                on_mode_df = on_mode_df.append(cdf.loc[test])
            abc_on_pwr = on_mode_df.loc[abc_on_tests, 'watts'].mean()
            abc_on_lum = on_mode_df.loc[abc_on_tests, 'nits'].mean()
            measured = {
                'nits': np.mean([abc_on_lum, abc_off_lum]),
                'watts': np.mean([abc_on_pwr, abc_off_pwr])
            }

            measured_name = f'{abc_off_test}_measured'
            on_mode_df = on_mode_df.append(pd.Series(data=measured, name=measured_name))
            limit = limit_func(area=area, luminance=on_mode_df.loc[measured_name, 'nits'])
            on_mode_df.loc[measured_name, 'limit'] = limit
        else:
            limit = limit_func(area=area, luminance=on_mode_df.loc[abc_off_test, 'nits'])
            on_mode_df.loc[abc_off_test, 'limit'] = limit
        return on_mode_df

    cdf = rsdf.set_index('test_name')
    on_mode_df = cdf.drop(cdf.index)
    
    def_abc_tests = [test for test in ['default_100', 'default_35', 'default_12', 'default_3'] if test in cdf.index]
    on_mode_df = add_pps_tests(on_mode_df, cdf, 'default', def_abc_tests, limit_funcs['default'])

    br_abc_tests = [test for test in ['brightest_100', 'brightest_35', 'brightest_12', 'brightest_3'] if
                    test in cdf.index]
    on_mode_df = add_pps_tests(on_mode_df, cdf, 'brightest', br_abc_tests, limit_funcs['brightest'])
    
    if hdr:
        hdr_abc_tests = [test for test in ['hdr10_100', 'hdr10_35', 'hdr10_12', 'hdr10_3'] if test in cdf.index]
        on_mode_df = add_pps_tests(on_mode_df, cdf, 'hdr10', hdr_abc_tests, limit_funcs['hdr10'])

    on_mode_df = on_mode_df.reset_index()

    
    if limit_type == 'estar':
        on_mode_df['result'] = (on_mode_df['watts'] < on_mode_df['limit']).apply({True: 'Pass', False: 'Fail'}.get)
    else:
        # on_mode_df['ratio'] = on_mode_df['watts'] / on_mode_df['limit']
        on_mode_df['gap'] =  on_mode_df['limit'] - on_mode_df['watts']
        data = {'test_name': 'average_measured', 'gap': on_mode_df['gap'].mean()}
        on_mode_df = on_mode_df.append(data, ignore_index=True)
    
    
    cols = ['test_name', 'preset_picture', 'abc', 'lux', 'nits', 'limit', 'watts', 'gap', 'result']
    cols = [col for col in cols if col in on_mode_df.columns]
    on_mode_df = on_mode_df[cols]
    return on_mode_df

@except_none_log
def get_standby_df(rsdf):
    """Create a dataframe and corresponding reportlab TableStyle data which displays the results of standby testing."""
    
    standby_df = rsdf[rsdf['test_name'].apply(lambda x: 'standby' in x)].copy()
    
    limits = {
        'standby': 2,
        'standby_echo': 2,
        'standby_google': 2,
        'standby_multicast': 2,
        'standby_passive': .5,
        'standby_active_low': 2,
    }
    standby_df['limit'] = standby_df['test_name'].apply(limits.get)
    cols = ['test_name', 'qs', 'lan', 'wan', 'waketime', 'limit', 'watts']
    cols = [col for col in cols if col in standby_df.columns]
    standby_df = standby_df.reset_index()[cols]
    standby_df['result'] = (standby_df['watts'] < standby_df['limit']).apply({True: 'Pass', False: 'Fail'}.get)

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
    if docopt_args['-e']:
        return 'estar'
    elif docopt_args['-v']:
        return 'alternative'
    elif docopt_args['-p']:
        return 'pcl'
    elif 'ENERGYSTAR' in data_folder.stem:
        return 'estar'
    elif 'VA' in data_folder.stem:
        return 'alternative'
    elif 'Alternative' in data_folder.stem:
        return 'alternative'
    elif 'PCL' in data_folder.stem:
        return 'pcl'
    else:
        warnings.warn('Report type could not be identified. Attempting ENERGYSTAR report...')
        return 'estar'
    return report_type

# @except_none_log
# def power_cap_funcs():
#     def power_cap(area, sf, a, b):
#         return sf * ((a * area) + b)
#     power_cap_coeffs = pd.read_csv(Path(sys.path[0]).joinpath(r'config\power-cap-coeffs.csv'), index_col='coef').to_dict()
#     power_cap_funcs = {func_name: partial(power_cap, **coeff_vals) for func_name, coeff_vals in
#                        power_cap_coeffs.items()}
#     return power_cap_funcs

@except_none_log
def get_adjustment_factor(test_specs_df):
    return test_specs_df.loc['POA_MAX Adjustment Factor', 0]


@except_none_log
def get_limit_funcs(limit_type, adjustment_factor='4K'):
    
    af_value = {
        'HD': .75,
        '4K': 1,
        '4K_HCR': 1.25,
        '8K': 1.25
    }.get(adjustment_factor)
    
    def power_cap(area, luminance, sf, a, b):
        return af_value * (sf * ((a * area) + b))
    power_cap_coeffs = pd.read_csv(Path(sys.path[0]).joinpath(r'config\power-cap-coeffs.csv'), index_col='coef').to_dict()
    power_cap_funcs = {func_name: partial(power_cap, **coeff_vals) for func_name, coeff_vals in power_cap_coeffs.items()}
    
    def power_limit(area, luminance, sf, a, b, c, d, power_cap_func=None):
        limit = af_value * (sf * ((a * area + b) * luminance + c * area + d))
        if power_cap_func is not None:
            return min(limit, power_cap_func(area, luminance))
        else:
            return limit
    
    coeffs = pd.read_csv(Path(sys.path[0]).joinpath(r'config\coeffs.csv'), index_col='coef').to_dict()
    # if limit_type == 'estar':
    for func_name in coeffs:
        coeffs[func_name]['power_cap_func'] = power_cap_funcs[func_name]

    limit_funcs = {func_name: partial(power_limit, **coeff_vals) for func_name, coeff_vals in coeffs.items()}
    return limit_funcs

@except_none_log
@permission_popup
def get_status_df(test_seq_df, merged_df, paths, data_folder):
    cols = ['tag', 'test_name', 'test_time']
    status_df = test_seq_df.copy()[cols]
    status_df = status_df[status_df['test_name'] != 'screen_config']
    status_df = status_df[~status_df['test_name'].str.contains('ccf')]
    if merged_df is not None and isinstance(merged_df, pd.DataFrame) and not merged_df.empty:
        def get_status(test_name):
        
            default_check = lambda: test_name in merged_df['test_name'].unique()
            status_checker = defaultdict(default_check)
            status_checker.update({
                'lum_profile': bool(paths.get('lum_profile')),
                'camera_ccf_default': bool(paths.get('ccf')),
                'stabilization': 'stabilization1' in merged_df['test_name'].unique(),
                'active_low_waketime': pd.notna(merged_df.query('test_name=="standby_active_low"').reset_index()['waketime'].get(0))
                    # pd.notna(
                    # merged_df[merged_df['test_name']=='standby_active_low'].iloc[0]['waketime'])
            })
            return {True: 'Run', False: 'Not Run'}.get(status_checker[test_name])
        status_df['status'] = status_df['test_name'].apply(get_status)
        def get_completion_time(row):
            if row['status'] == 'Run':
                if row['test_name'] in merged_df['test_name'].unique():
                    return merged_df.groupby('test_name').last().loc[row['test_name']]['time']
                elif row['test_name'] == 'stabilization':
                    mask = merged_df['test_name'].apply(lambda test_name: 'stabilization' in test_name)
                    return merged_df[mask].iloc[-1]['time']
                elif row['test_name'] == 'lum_profile':
                    return str(pd.Timestamp(os.path.getmtime(paths.get('lum_profile')), unit='s'))

                
        status_df['completion_time'] = status_df.apply(get_completion_time, axis=1)
    else:
        status_df['status'] = 'Not Run'
        status_df['completion_time'] = None
    status_df.to_csv(data_folder.joinpath('test-status.csv'), index=False)
    return status_df

@except_none_log
@permission_popup
def get_test_seq_df(paths):
    return pd.read_csv(paths['test_seq'])
    
@except_none_log
@permission_popup
def get_merged_df(test_seq_df, paths, data_folder):
    
    data_df = pd.read_csv(paths['test_data'], parse_dates=['Timestamp'])
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
    
    
    return merged_df

@except_none_log
def get_spectral_df(paths):
    df = pd.read_csv(paths['spectral_profile']).iloc[39:]
    
    df = df.astype(float).set_index(df.columns[0])
    df = df[df.columns[:4]]
    df.columns = [i.split('(')[0].strip() for i in df.columns]
    df.index.name = 'Wavelength (nm)'
    return df

@except_none_log
@permission_popup
def get_contrast_ratio(paths):
    contrast_df = pd.read_csv(paths['contrast'], header=None).set_index(0).T
    white = contrast_df['white'].iloc[0]
    black = contrast_df['black'].iloc[0]
    return white/black

@except_none_log
@permission_popup
def get_spectral_summary_df(data):
    ss_data = {
        'BT2020 Coverage': data['bt2020_coverage'],
        'BT709 Coverage': data['bt709_coverage'],
        'Contrast Ratio': data['contrast_ratio'],
        '75% Brightness Loss Angle': data['brightness_loss_crossover'],
        '80% Color Washout Angle Red': data['washout_crossovers']['Red'],
        '80% Color Washout Angle Green': data['washout_crossovers']['Green'],
        '80% Color Washout Angle Blue': data['washout_crossovers']['Blue'],
        '3 degree Color Shift Angle Red': data['color_shift_crossovers']['positive']['Red'],
        '3 degree Color Shift Angle Green': data['color_shift_crossovers']['positive']['Green'],
        '3 degree Color Shift Angle Blue': data['color_shift_crossovers']['positive']['Blue'],
        '-3 degree Color Shift Angle Red': data['color_shift_crossovers']['negative']['Red'],
        '-3 degree Color Shift Angle Green': data['color_shift_crossovers']['negative']['Green'],
        '-3 degree Color Shift Angle Blue': data['color_shift_crossovers']['negative']['Blue'],
    }
    spectral_summary_df = pd.DataFrame(ss_data, index=[0]).T
    save_path = data['data_folder'].joinpath('spectral_summary.csv')
    spectral_summary_df.to_csv(save_path, header=False)
    return spectral_summary_df

@except_none_log
def get_spectral_coordinates_df(paths):
    df = pd.read_csv(paths['spectral_profile']).iloc[18:20]
    df = df.set_index(df.columns[0]).astype(float)
    df.index.name = ''
    df = df[['Red(0)', 'Green(0)', 'Blue(0)']]
    df.columns = ['Red', 'Green', 'Blue']
    return df.reset_index()

@except_none_log
def get_washout_df(paths):
    df = pd.read_csv(paths['spectral_profile'])
    df = df.set_index(df.columns[0])
    df.index.name = ''
    df = df.iloc[12:15].T

    df = df.reset_index()

    df['color'] = df['index'].apply(lambda s: s.split('(')[0].strip())
    df['angle'] = df['index'].apply(lambda s: s.split('(')[1].replace(')', '')).astype(int)

    df['X'] = df['X'].astype(float)
    df['Y'] = df['Y'].astype(float)
    df['Z'] = df['Z'].astype(float)

    df['normX'] = (df['X']/df['X'][0]).apply(lambda x: min(x, 1))
    df['normY'] = (df['Y']/df['Y'][0]).apply(lambda x: min(x, 1))
    df['normZ'] = (df['Z']/df['Z'][0]).apply(lambda x: min(x, 1))
    lab = df[['normX', 'normY', 'normZ']].apply(XYZ_to_Lab, axis=1)
    df['lchab'] = lab.apply(Lab_to_LCHab)
    df['l'] = df['lchab'].apply(lambda x: x[0])

    df['c'] = df['lchab'].apply(lambda x: x[1])
    df['h'] = df['lchab'].apply(lambda x: x[2])
    df = df[['color', 'angle', 'l', 'c', 'h']].set_index(['color', 'angle'])
    df = df['c'].to_frame().reset_index()
    df = df.pivot(index='angle', columns='color')
    df.columns = [i[1] for i in df.columns]
    for col in df.columns:
        df[col] = (df[col]/df[col].values[0]).apply(lambda x: min(x, 1))
    df = df.drop('White', axis=1)
    return df

@except_none_log
def get_color_shift_df(paths):
    df = pd.read_csv(paths['spectral_profile'])
    df = df.set_index(df.columns[0])
    df.index.name = ''

    df = df.iloc[12:15].T

    df = df.reset_index()

    df['color'] = df['index'].apply(lambda s: s.split('(')[0].strip())
    df['angle'] = df['index'].apply(lambda s: s.split('(')[1].replace(')', '')).astype(int)

    df['X'] = df['X'].astype(float)
    df['Y'] = df['Y'].astype(float)
    df['Z'] = df['Z'].astype(float)

    df['normX'] = (df['X']/df['X'][0]).apply(lambda x: min(x, 1))
    df['normY'] = (df['Y']/df['Y'][0]).apply(lambda x: min(x, 1))
    df['normZ'] = (df['Z']/df['Z'][0]).apply(lambda x: min(x, 1))
    lab = df[['normX', 'normY', 'normZ']].apply(XYZ_to_Lab, axis=1)
    df['lchab'] = lab.apply(Lab_to_LCHab)
    df['l'] = df['lchab'].apply(lambda x: x[0])
    df['l'] = df['l']
    df['c'] = df['lchab'].apply(lambda x: x[1])
    df['h'] = df['lchab'].apply(lambda x: x[2])
    df = df[['color', 'angle', 'l', 'c', 'h']].set_index(['color', 'angle'])
    df = df['h'].to_frame().reset_index()
    df = df.pivot(index='angle', columns='color')
    df.columns = [i[1] for i in df.columns]
    for col in df.columns:
        df[col] = (df[col]-df[col].values[0])
    df = df.drop('White', axis=1)
    return df

@except_none_log
def get_brightness_loss_df(paths):
    df = pd.read_csv(paths['spectral_profile'])
    df = df.set_index(df.columns[0])
    df.index.name = ''
    df = df.iloc[12:15].T
    df = df.reset_index()
    df['color'] = df['index'].apply(lambda s: s.split('(')[0].strip())
    df['angle'] = df['index'].apply(lambda s: s.split('(')[1].replace(')', '')).astype(int)
    df['Y'] = df['Y'].astype(float)
    df['normY'] = (df['Y'] / df['Y'][0]).apply(lambda x: min(x, 1))
    df = df[['color', 'angle', 'normY']]
    df = df.pivot(index='angle', columns='color')
    df.columns = [i[1] for i in df.columns]
    return df[['White']]


def get_crossover_x(series, crossover_y):
    dc_mask = (series > crossover_y) & (crossover_y > series.shift(-1))
    dc_masked_series = series[dc_mask]
    crossover_x = None
    if len(dc_masked_series) > 0:
        x1 = dc_masked_series.index[0]

        x2 = series.index[list(series.index).index(x1) + 1]
        y1 = series.loc[x1]
        y2 = series.loc[x2]
        slope = (y2 - y1) / (x2 - x1)
        crossover_x = x1 + (crossover_y - y1) / slope
        return crossover_x
    uc_mask = ((series > crossover_y) & (crossover_y > series.shift(1)))
    uc_masked_series = series[uc_mask]
    if len(uc_masked_series) > 0:
        x1 = uc_masked_series.index[0]

        x2 = series.index[list(series.index).index(x1) - 1]
        y1 = series.loc[x1]
        y2 = series.loc[x2]
        slope = (y2 - y1) / (x2 - x1)
        crossover_x = x1 + (crossover_y - y1) / slope
        return crossover_x
    return crossover_x

@except_none_log
def get_washout_crossovers(washout_df):
    crossovers = {}
    for col in washout_df.columns:
        crossovers[col] = get_crossover_x(series=washout_df[col], crossover_y=.8)
    return crossovers

@except_none_log
def get_color_shift_crossovers(color_shift_df):
    pos_crossovers = {}
    for col in color_shift_df.columns:
        pos_crossovers[col] = get_crossover_x(series=color_shift_df[col], crossover_y=3)
    neg_crossovers = {}
    for col in color_shift_df.columns:
        neg_crossovers[col] = get_crossover_x(series=color_shift_df[col], crossover_y=-3)
    crossovers = {
        'positive': pos_crossovers,
        'negative': neg_crossovers
    }
    return crossovers

@except_none_log
def get_brightness_loss_crossover(brightness_loss_df):
    return get_crossover_x(series=brightness_loss_df['White'], crossover_y=.75)
    
@except_none_log
def get_coverage(coordinates_df, colorspace):
    def point_on_triangle(pt1, pt2, pt3):
        """Random point on the triangle with vertices pt1, pt2 and pt3."""
        s, t = sorted([random.random(), random.random()])
        return (s * pt1[0] + (t - s) * pt2[0] + (1 - t) * pt3[0],
                s * pt1[1] + (t - s) * pt2[1] + (1 - t) * pt3[1])
    
    def isInside(x1, y1, x2, y2, x3, y3, x, y):
        """A function to check whether point P(x, y) lies inside the triangle formed by A(x1, y1), B(x2, y2) and C(x3, y3)"""
        
        def area(x1, y1, x2, y2, x3, y3):
            """A utility function to calculate area of triangle formed by (x1, y1), (x2, y2), and (x3, y3)"""
            return abs((x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2.0)
            # Calculate area of triangle ABC
        
        A = area(x1, y1, x2, y2, x3, y3)
        # Calculate area of triangle PBC
        A1 = area(x, y, x2, y2, x3, y3)
        # Calculate area of triangle PAC
        A2 = area(x1, y1, x, y, x3, y3)
        # Calculate area of triangle PAB
        A3 = area(x1, y1, x2, y2, x, y)
        # Check if sum of A1, A2 and A3
        # is same as A (rounding to avoid inequalities caused by floating point arithmetic)
        if round(A, 10) == round(A1 + A2 + A3, 10):
            return True
        else:
            return False
    
    x1, y1, x2, y2, x3, y3 = coordinates_df[['Red', 'Green', 'Blue']].T.values.ravel()
    total, inside_total = 0, 0
    for _ in range(100000):
        x, y = point_on_triangle(*colorspace._primaries)
        inside_total += isInside(x1, y1, x2, y2, x3, y3, x, y)
        total += 1
    return inside_total / total

@except_none_log
def get_lum_df(paths):
    lum_df = pd.read_csv(paths['lum_profile'], header=None)
    height, width = lum_df.shape
    lum_df.columns = map(lambda x: 100 * x / width, lum_df.columns)
    lum_df.index = map(lambda x: 100 * (1 - x / height), lum_df.index)
    return lum_df

@except_none_log
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
def get_model(test_specs_df, clean=False):
    if clean:
        return 'Model XXXXXXXX'
    else:
        return f"{str(test_specs_df.loc['Make', 0]).upper()} {str(test_specs_df.loc['Model', 0]).upper()}"

@except_none_log
def get_setup_img_paths(paths, data_folder):
    setup_img_dir = Path(data_folder).joinpath('SetupImg')
    setup_img_dir.mkdir(exist_ok=True)
    
    img_paths = pd.read_csv(paths['setup_images'], header=None)[0]
    img_paths = img_paths.apply(lambda img_path: Path(img_path))
    # img_paths = [Path(img_path_str) for img_path_str in img_paths]
    if not img_paths.apply(lambda img_path: setup_img_dir==img_path.parent).all():
        for i, img_path in img_paths.items():
            if setup_img_dir != img_path.parent:
                new_img_path = setup_img_dir.joinpath(img_path.name)
                shutil.copyfile(src=img_path, dst=new_img_path)
                img_paths.loc[i] = new_img_path
        img_paths.to_frame().to_csv(paths['setup_images'], header=None, index=None)
    return img_paths.to_list()
    
@except_none_log
def get_3bar_lum_df(paths):
    return pd.read_csv(paths['bar3_lum'])

@except_none_log
def get_dimming_line_df(rsdf, data_folder):
    dimming_line_df = pd.DataFrame(columns=['pps', 'slope', 'intercept', 'r2'])
    for pps in ['default', 'brightest', 'hdr']:
        pps_df = rsdf[rsdf['test_name'].str.contains(pps)]
        if len(pps_df) > 1:
            x, y = pps_df['nits'], pps_df['watts']
            slope, intercept, r, _, _ = linregress(x, y)
            r2 = r ** 2
            row_data = {'pps': pps, 'slope': slope, 'intercept': intercept, 'r2': r2}
            dimming_line_df = dimming_line_df.append(row_data, ignore_index=True)
    dimming_line_df.to_csv(data_folder.joinpath('dimming-lines.csv'), index=False)
    return dimming_line_df

def get_report_data(paths, data_folder, docopt_args):
    data = {}
    data['clean'] = docopt_args['-c']
    data['data_folder'] = data_folder
    data['report_type'] = get_report_type(docopt_args, data_folder)
    data['omit_estar'] = docopt_args['--omit']
    data['test_seq_df'] = get_test_seq_df(paths)
    data['merged_df'] = get_merged_df(data['test_seq_df'], paths, data_folder)
    data['hdr'] = get_hdr(data['merged_df'])
    data['test_specs_df'] = get_test_specs_df(data['merged_df'], paths, data['report_type'], clean=data['clean'])
    data['adjustment_factor'] = get_adjustment_factor(data['test_specs_df'])
    data['estar_limit_funcs'] = get_limit_funcs('estar', data['adjustment_factor'])
    data['va_limit_funcs'] = get_limit_funcs('alternative', data['adjustment_factor'])
    # data['estar_limit_funcs'] = get_limit_funcs('estar', data['adjustment_factor'])
    data['setup_img_paths'] = get_setup_img_paths(paths, data_folder)
    data['bar3_lum_df'] = get_3bar_lum_df(paths)
    if data['report_type']=='pcl':
        data['persistence_dfs'] = get_persistence_dfs(paths)
    if paths['spectral_profile'] is not None:
        data['spectral_df'] = get_spectral_df(paths)
        data['scdf'] = get_spectral_coordinates_df(paths)
        data['bt2020_coverage'] = get_coverage(data['scdf'], BT2020_COLOURSPACE)
        data['bt709_coverage'] = get_coverage(data['scdf'], BT709_COLOURSPACE)
        data['washout_df'] = get_washout_df(paths)
        data['washout_crossovers'] = get_washout_crossovers(data['washout_df'])
        data['color_shift_df'] = get_color_shift_df(paths)
        data['color_shift_crossovers'] = get_color_shift_crossovers(data['color_shift_df'])
        data['brightness_loss_df'] = get_brightness_loss_df(paths)
        data['brightness_loss_crossover'] = get_brightness_loss_crossover(data['brightness_loss_df'])
        data['contrast_ratio'] = get_contrast_ratio(paths)
        data['spectral_summary_df'] = get_spectral_summary_df(data)

    else:
        data['persistence_dfs'] = None
        data['spectral_df'] = None
        data['scdf'] = None
        data['washout_df'] = None
        data['washout_crossovers'] = None
        data['color_shift_df'] = None
        data['color_shift_crossovers'] = None
        data['brightness_loss_df'] = None
        data['brightness_loss_crossover'] = None
    data['waketimes'] = get_waketimes(data['merged_df'])
    data['rsdf'] = get_results_summary_df(data['merged_df'], data_folder, data['waketimes'])
    
    data['test_date'] = get_test_date(data['test_specs_df'])
    data['area'] = get_screen_area(data['test_specs_df'])
    data['model'] = get_model(data['test_specs_df'], clean=data['clean'])
    data['estar_on_mode_df'] = get_on_mode_df(data['rsdf'], data['estar_limit_funcs'], data['area'], 'estar', data['hdr'])
    data['va_on_mode_df'] = get_on_mode_df(data['rsdf'], data['va_limit_funcs'], data['area'], 'alternative', data['hdr'])
    # data['estar_on_mode_df'] = get_on_mode_df(data['rsdf'], data['limit_funcs'], data['area'], 'estar', data['hdr'])
    data['standby_df'] = get_standby_df(data['rsdf'])
    data['status_df'] = get_status_df(data['test_seq_df'], data['merged_df'], paths, data['data_folder'])
    data['lum_df'] = get_lum_df(paths)
    get_dimming_line_df(data['rsdf'], data_folder)
    # data['csdf'] = get_compliance_summary_df(data['on_mode_df'], data['standby_df'], data['report_type'], data['hdr'])
    
    
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