"""Usage:
pcl_sequence.exe <data_folder>
"""

import pandas as pd
import sys
import shutil
from pathlib import Path
import PySimpleGUI as sg
import os
from docopt import docopt

import sequence as ts
import command_sequence as cs
import logfuncs as lf


CCF_PPS_LIST = ['default']


def get_test_order(pps_df):

    test_order = ts.setup_tests(CCF_PPS_LIST)
    test_order += [
        'default',
        'default_3bar',
        'brightest',
        'brightest_10%sdr',
        # 'hdr10'
    ]
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
        'standby',
        'waketime',
        'standby_echo',
        'echo_waketime',
        'standby_google',
        'google_waketime',
    ]
    return test_order


def gui_window():
    layout = [
        [sg.Text('TV Model')],
        [sg.InputText(key='model')],
        [sg.Text('Destination Folder')],
        [sg.Input(key='destination_folder'), sg.FolderBrowse()],
        [sg.Submit()]
    ]
    window = sg.Window('Test Sequence Input').Layout(layout)
    _, values = window.Read()
    window.close()
    return values


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
    
    # path = 'C:\\Users\\rhohe\\Documents\\JupyterScratch\\Samsung_666\\Samsung666-entry-forms.xlsx'
    df = pd.read_excel(path, sheet_name='PPS', index_col=0)
    
    df = df.dropna(subset=['PPS Name']).replace({'y': True, 'n': False})
    df = df.rename(columns={'PPS Name': 'pps_name', 'ABC Enabled Y/N': 'abc'}, index=base_tests)
    df['pps_labels'] = pd.Series(df.index, index=df.index).apply(pps_labels.get)
    return df


def get_qson(path):
    df = pd.read_excel(path, sheet_name='Misc', index_col=0)
    df.columns = ['entry']
    df = df.replace({'y': True, 'n': False})
    qson_def = df.loc['Does QS default to On', 'entry']
    qs_10 = df.loc['Does QS require ≥ 10 sec to wake and display HDMI signal?', 'entry']
    return qson_def or qs_10
    
    
def main():
    logger = lf.cwd_logger('pcl-sequence.log')
    # values = gui_window()
    docopt_args = docopt(__doc__)
    logger.info(docopt_args)
    
    # destination_folder = Path(values['destination_folder'])
    # data_folder = destination_folder.joinpath(values['model'])
    data_folder = Path(docopt_args['<data_folder>'])
    data_folder.mkdir(exist_ok=True)
    entry_forms_template = Path(sys.path[0]).joinpath('entry-forms.xlsx')
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
    
    test_seq_df = ts.create_test_seq_df(test_order, rename_pps, qson=get_qson(entry_forms))
    logger.info('\n' + test_seq_df.to_string())
    
    command_df = cs.create_command_df(test_seq_df)
    
    ts.save_sequences(test_seq_df, command_df, data_folder)


if __name__ == '__main__':
    main()
