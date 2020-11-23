"""Usage:
pcl_sequence.exe <data_folder>
"""
from functools import partial
import pandas as pd
import sys
import shutil
from pathlib import Path
import PySimpleGUI as sg
import os
import core.sequence.sequence as ts
import core.sequence.command_sequence as cs
import core.logfuncs as lf
from core.error_handling import error_popup


blank_entry_msg = lambda path, entry: f'Error in {path}\n\n"{entry}" cannot be blank.\nPress OK when error has been corrected.\nRemember to save.'
    
    
def get_test_order(pps_df):
    ccf_pps_list = ['default'] #, 'brightest']
    if 'hdr10' in pps_df.index and pd.notna(pps_df.loc['hdr10', 'pps_name']):
        ccf_pps_list += ['hdr10_default']
    test_order = ts.setup_tests(ccf_pps_list)
    test_order += [
        'default',
        # 'default_3bar',
        'brightest',
        # 'brightest_10%sdr',
        # 'hdr10'
    ]
    if 'hdr10' in pps_df.index and pd.notna(pps_df.loc['hdr10', 'pps_name']):
        test_order += ['hdr10']
    for lux_level in [None, 'low_backlight', 100, 35, 12, 3]:
        for base_test, row in pps_df.iterrows():
            test_name = None
            if lux_level is None:
                if base_test not in ['default', 'brightest', 'hdr'] and not row['abc']:
                    test_name = base_test
            elif lux_level == 'low_backlight':
                if not row['abc']:
                    test_name = f"{base_test}_{lux_level}"
            elif row['abc']:
                test_name = f"{base_test}_{lux_level}"
            if test_name:
                test_order.append(test_name)
    
    test_order += [
        'standby_passive',
        'passive_waketime',
        'standby_active_low',
        'active_low_waketime',
        'standby_multicast',
        'multicast_waketime',
        'standby_echo',
        'echo_waketime',
        'standby_google',
        'google_waketime',
    ]
    return test_order


def get_pps_df(path):
    base_tests = {
        'Default SDR PPS': 'default',
        'Brightest SDR PPS': 'brightest',
        'Default HDR10 PPS': 'hdr10',
        'Default HLG PPS': 'hlg',
        'Default HDR1000 PPS': 'hdr1000',
        'Default HDR10+ PPS': 'hdr10+',
        'PPS3': 'pps3',
        'PPS4': 'pps4',
        'PPS5': 'pps5',
        'PPS6': 'pps6',
        'PPS7': 'pps7',
        'PPS8': 'pps8',
        'PPS9': 'pps9',
        'PPS10': 'pps10',
        'PPS11': 'pps11',
        'PPS12': 'pps12'
    }
    
    pps_labels = {
        'default': 'default',
        'brightest': 'brightest',
        'hdr10': 'hdr10_default',
        'hlg': 'hlg_default',
        'hdr1000': 'hdr1000_default',
        'hdr10+': 'hdr10+_default',
        'pps3': 'pps3',
        'pps4': 'pps4',
        'pps5': 'pps5',
        'pps6': 'pps6',
        'pps7': 'pps7',
        'pps8': 'pps8',
        'pps9': 'pps9',
        'pps10': 'pps10',
        'pps11': 'pps11',
        'pps12': 'pps12'
    }
    
    df = pd.read_excel(path, sheet_name='PPS', index_col=0)
    df = df.dropna(subset=['PPS Name']).replace({'y': True, 'n': False})
    
    for pps in ['Default SDR PPS', 'Brightest SDR PPS']:
        if pps not in df.index:
            error_popup(blank_entry_msg(path, pps), partial(get_pps_df, path=path))

    df = df.rename(columns={'PPS Name': 'pps_name', 'ABC Enabled By Default (Y/N)': 'abc'}, index=base_tests)
    df['pps_labels'] = pd.Series(df.index, index=df.index).apply(pps_labels.get)
    return df



    
    
def get_qsinfo(path):
    df = pd.read_excel(path, sheet_name='Misc', index_col=0)
    df.columns = ['entry']
    df['entry'] = df['entry'].astype(object)
    df = df.replace({'Yes': True, 'No': False})

    def check_entry(idx):
        entry = df.loc[idx, 'entry']
        if pd.isnull(entry):
            ts.error_popup(blank_entry_msg(path, idx), partial(get_qson, path))
        return entry
    
    has_qs = check_entry('Does TV have QS?')
    if has_qs:
        qsoff_def = check_entry('Does QS default to Off?')
        qs_secs = check_entry('If so, how many seconds does it take to wake to HDMI signal?')
        qs_10 = qs_secs >= 10
        qson = qsoff_def and qs_10
    else:
        qson = False
        
    return {
        'qs': has_qs,
        'qson': qson
    }
    
    
def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'pcl-sequence.log')

    entry_forms_template = Path(sys.path[0]).joinpath(r'config\entry-forms.xlsx')
    entry_forms = Path(data_folder).joinpath("entry-forms.xlsx")
    
    logger.info(f'Entry Forms Exist: {entry_forms.exists}')
    if not entry_forms.exists():
        shutil.copy(entry_forms_template, entry_forms)
    
    try:
        os.system(str(entry_forms))
    except:
        pass

    layout = [
        [sg.Text('Enter info in entry forms and press Ok to continue')],
        [sg.Ok()]
    ]
    sg.Window('Title').Layout(layout).Read()
    
    pps_df = get_pps_df(entry_forms)
    logger.info('\n' + pps_df.to_string())
    
    test_order = get_test_order(pps_df)
    logger.info(test_order)
    
    rename_pps = dict(zip(pps_df.pps_labels, pps_df.pps_name))
    logger.info(rename_pps)
    
    qs_info = get_qsinfo(entry_forms)
    test_seq_df = ts.create_test_seq_df(test_order, rename_pps, **qs_info)
    logger.info('\n' + test_seq_df.to_string())
    
    command_df = cs.create_command_df(test_seq_df)
    
    ts.save_sequences(test_seq_df, command_df, data_folder)


if __name__ == '__main__':
    main()
