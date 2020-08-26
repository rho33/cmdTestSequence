"""Usage:
mock_data.py
mock_data.py <data_folder>
"""
import sys
import shutil
from pathlib import Path
import pandas as pd
import numpy as np
import PySimpleGUI as sg
from docopt import docopt
sys.path.append('..')
import filefuncs as ff


def get_intro_df(tag):
    seconds = np.random.randint(30, 100)
    data = {
        'Timestamp': None,
        'Tag': f'{tag} - user command',
        'Luminance': 20*np.random.rand(seconds),
        'Power': 100*np.random.rand(seconds),
        'Voltage': [120.0]*seconds,
        'Frequencey': [60.0]*seconds,
        'Serial Buffer': None,
        'Max Luminance': 1000*np.random.rand(seconds),
        'Camera Temperature': 49 + 2*np.random.rand(seconds),
    }
    return pd.DataFrame(data)


def get_test_df(row, apl_folder):
    adj_factors = {
        'default': 1,
        'brightest': 1.2,
        'hdr': 1.3,
    }
    af = None
    for pps, adj_factor in adj_factors.items():
        if pps in row['test_name']:
            af = adj_factor
    if af is None:
        af = .7 + .6 * np.random.rand()
    af *= 3
    
    apl_path = Path(apl_folder).joinpath(f"{row['video']}-APL.csv")
    if apl_path.exists():
        apl = pd.read_csv(apl_path)["APL'"].values
    else:
        apl = [1]
    
    if pd.notnull(row['test_time']):
        seconds = int(row['test_time'])
    else:
        seconds = 9
    
    apl = np.tile(apl, 1 + seconds // len(apl))[:seconds]
    add_noise = lambda arr, stdev_pct: arr + arr * stdev_pct * np.random.randn(len(arr))
    power = add_noise(af * apl, .05)
    luminance = add_noise(power * .5, .05)
    max_lum = add_noise(luminance * 4.5, .25)
    
    data = {
        'Timestamp': None,
        'Tag': row['tag'],
        'Luminance': luminance,
        'Power': power,
        'Voltage': [120.0] * seconds,
        'Frequencey': [60.0] * seconds,
        'Serial Buffer': None,
        'Max Luminance': max_lum,
        'Camera Temperature': 49 + 2 * np.random.rand(seconds),
    }
    df = pd.DataFrame(data)
    return df


def get_mock_df(test_seq_df, apl_folder, repair=False):
    df_list = []
    for i, row in test_seq_df.iterrows():
        if row['test_name']=='stabilization':
            stab_df_list = []
            row['test_time'] = 600
            tag = row['tag']
            for i in range(2):
                stab_tag = f"{tag} - stabilization {i+1}"
                row['tag'] = stab_tag
                stab_test_df = pd.concat([get_intro_df(tag), get_test_df(row, apl_folder)], ignore_index=True)
                stab_df_list.append(stab_test_df)
            stab_df = pd.concat(stab_df_list, ignore_index=True)
            df_list.append(stab_df)
        else:
            df = pd.concat([get_intro_df(row['tag']), get_test_df(row, apl_folder)])
            df_list.append(df)
    mock_df = pd.concat(df_list, ignore_index=True)
    if repair:
        mock_df['Timestamp'] = pd.date_range(start=pd.Timestamp.now(), periods=len(mock_df), freq='S')
    else:
        mock_df['Timestamp'] = pd.date_range(end=pd.Timestamp.now(), periods=len(mock_df), freq='S')
    return mock_df


def gui_window():
    layout = [
        [sg.Text('Test Sequence')],
        [sg.Input(key='test_seq'), sg.FileBrowse()],
        [sg.Submit()],
    ]
    window = sg.Window('Test Sequence Input').Layout(layout)
    _, values = window.Read()
    window.close()
    return values


def main():
    docopt_args = docopt(__doc__)
    if docopt_args['<data_folder>']:
        data_folder = Path(docopt_args['<data_folder>'])
        paths = ff.get_paths(data_folder)
        test_seq_df = pd.read_csv(paths['test_seq'])
    else:
        values = gui_window()
        test_seq_df = pd.read_csv(values['test_seq'])
        data_folder = Path(values['test_seq']).parent
    repair = 'Repair' in str(data_folder)
    apl_folder = r"APL"
    df = get_mock_df(test_seq_df, apl_folder, repair)
    save_path = data_folder.joinpath('mock-datalog.csv')
    df.to_csv(str(save_path), index=False)
    if not repair:
        lum_save_path = save_path.parent.joinpath('mock_lum profile.csv')
        shutil.copyfile(src=Path(sys.path[0]).joinpath('mock_lum profile.csv'), dst=lum_save_path)
        metadata_save_path = save_path.parent.joinpath('mock-test-metadata.csv')
        shutil.copyfile(src=Path(sys.path[0]).joinpath('mock-test-metadata.csv'), dst=metadata_save_path)


if __name__ == '__main__':
    main()