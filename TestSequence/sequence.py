import sys
import shutil
from datetime import datetime
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s:%(name)s:%(message)s')
file_handler = logging.FileHandler('sample.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def get_tests():
    """Construct dictionary of all possible tests from csv file."""
    path = Path(sys.path[0]).joinpath('test-details.csv')
    df = pd.read_csv(path).T
    df.columns = df.iloc[0]
    tests = df.to_dict()
    return tests


# def all_setup_tests():
#     tests = get_tests()
#     all_setup_tests = [test for test in tests.keys() if test in ['screen_config', 'stabilization'] or 'ccf' in test]
#     print(all_setup_tests)
#     return all_setup_tests


def setup_tests(pps_list, lum_profile=True):
    
    test_order = [f"ref_ccf_{pps}" for pps in pps_list]
    test_order += ['screen_config']
    test_order += [f"basler_ccf_{pps}" for pps in pps_list]
    if lum_profile:
        test_order += ['lum_profile']
    test_order += ['stabilization']
    return test_order

def create_test_seq_df(test_order, rename_pps, qson=False):
    """Construct test sequence DataFrame"""
    tests = get_tests()
    columns = ['test_name', 'test_time', 'video', 'preset_picture', 'abc', 'backlight', 'lux', 'mdd', 'qs', 'special_commands']
    df = pd.DataFrame(columns=columns)
    for test in test_order:
        df = df.append(tests[test], ignore_index=True)
    ccf_pps_list = df[df['test_name'].str.contains('ccf')]['preset_picture'].unique()
    for i, row in df.iterrows():
        if 'basler' in row['test_name']:
            last_basler_idx = i
    prev_pps = None
    for i, row in df.loc[last_basler_idx+1:].iterrows():
        if row['preset_picture'] != prev_pps and pd.notna(row['preset_picture']) and row['preset_picture'] in ccf_pps_list:
            if pd.isna(row['special_commands']):
                df.loc[i, 'special_commands'] = f"load_ccf:{row['preset_picture']}"
            else:
                df.loc[i, 'special_commands'] = f"load_ccf:{row['preset_picture']}," + df.loc[i, 'special_commands']
            prev_pps = row['preset_picture']
            
    prev_peak = False
    for i, row in df.loc[last_basler_idx+1:].iterrows():
        peak = pd.notna(row['special_commands']) and 'peak_test:1' in row['special_commands']
        if prev_peak and not peak:
            if pd.isna(row['special_commands']):
                df.loc[i, 'special_commands'] = 'peak_test:end'
            else:
                df.loc[i, 'special_commands'] += ',peak_test:end'
        prev_peak = peak
        
    if qson:
        df['qs'] = df['qs'].replace('off', 'on')
    # else:
    #     df['qs'] = df['qs'].replace('oob', 'off')

    df['preset_picture'] = df['preset_picture'].replace(rename_pps)
    df.index = range(1, len(df) + 1)
    df.index.name = 'tag'
    return df.reset_index()


def archive(filepath, copy=True, date=False):
    path = Path(filepath)
    archive_dir = path.parent.joinpath('Archive')
    if not archive_dir.exists():
        archive_dir.mkdir()

    if date:
        today = datetime.today().strftime('%Y-%h-%d-%H-%M')
        save_path = archive_dir.joinpath(f'{path.stem}-{today}{path.suffix}')
    else:
        save_path = archive_dir.joinpath(f'{path.name}')

    if copy:
        shutil.copyfile(path, save_path)
    else:
        shutil.move(path, save_path)
        
        
def save_sequences(test_seq_df, command_df, data_folder, repair=False):
    filenames = ['test-sequence.csv', 'command-sequence.csv']
    test_seq_df.to_csv(filenames[0], index=False)
    command_df.to_csv(filenames[1], index=False, header=False)
    for filename in filenames:
        if repair:
            repair_folder = Path(data_folder).joinpath('Repair')
            repair_folder.mkdir(exist_ok=True)
            save_path = repair_folder.joinpath(f"repair-{filename}")
        else:
            save_path = Path(data_folder).joinpath(filename)
            
        if save_path.exists():
            archive(save_path, date=True)
        shutil.copy(filename, save_path)
    
    
    
    