"""Functions used in multiple test sequence scripts."""
import sys
from datetime import datetime
import pandas as pd
from pathlib import Path
from ..filefuncs import archive, APPDATA_DIR
from ..error_handling import permission_popup


def get_tests():
    """Construct dictionary of all possible tests from csv file."""
    path = Path(sys.path[0]).joinpath(r'config\test-details.csv')
    
    df = pd.read_csv(path).T
    df.columns = df.iloc[0]
    tests = df.to_dict()
    return tests


def setup_tests(ccf_pps_list, lum_profile=True):
    """Construct list of setup tests meant to go at beginning of a test sequence"""
    
    # include a ref_ccf test for each preset picture setting requiring a color correction factor
    # test_order = [f"ref_ccf_{pps}" for pps in ccf_pps_list]
    # followed by the screen_config test
    test_order = ['screen_config', 'stabilization']
    # followed by a camera_ccf test for each ccf pps
    test_order += [f"camera_ccf_{pps}" for pps in ccf_pps_list]
    if lum_profile:
        test_order += ['lum_profile']
    return test_order


def create_test_seq_df(test_order, rename_pps, qs, qson=False):
    """Construct the test sequence DataFrame"""
    tests = get_tests()
    # columns argument ensures order of columns. Columns not listed (if any) will still appear after columns listed here
    columns = ['test_name', 'test_time', 'video', 'preset_picture', 'abc', 'backlight', 'lux']
    if qs:
        columns += ['qs']
    columns += ['lan', 'wan', 'special_commands',] # 'ccf_pps']
    df = pd.DataFrame(columns=columns)
    for test in test_order:
        df = df.append(tests[test], ignore_index=True)
    
    # get last ccf test so we know when to start adding load_ccf and peak commands
    last_ccf_idx = df[df['test_name'].str.contains('ccf')].index[-1]
    prev_ccf_pps = None
    prev_peak = False
    first = True
    for idx, row in df.loc[last_ccf_idx+1:].iterrows():
        # apply load_ccf command
        if first:
            if pd.isna(row['special_commands']):
                df.loc[idx, 'special_commands'] = f"load_ccf:default"
            else:
                df.loc[idx, 'special_commands'] = f"load_ccf:default," + df.loc[idx, 'special_commands']
            first = False
        # if pd.notna(row['ccf_pps']):
        #     if pd.isna(row['special_commands']):
        #         df.loc[idx, 'special_commands'] = f"load_ccf:{row['ccf_pps']}"
        #     else:
        #         df.loc[idx, 'special_commands'] = f"load_ccf:{row['ccf_pps']}," + df.loc[idx, 'special_commands']
        #     prev_ccf_pps = row['ccf_pps']
        # apply correct peak commands if any
        peak = pd.notna(row['special_commands']) and 'peak_test:1' in row['special_commands']
        if prev_peak and not peak:
            if pd.isna(row['special_commands']):
                df.loc[idx, 'special_commands'] = 'peak_test:end'
            else:
                df.loc[idx, 'special_commands'] += ',peak_test:end'
        prev_peak = peak
        
    if qs and qson:
        df['qs'] = df['qs'].replace('off', 'on')
    df['preset_picture'] = df['preset_picture'].replace(rename_pps)
    df.index = range(1, len(df) + 1)
    df.index.name = 'tag'
    return df.reset_index()

        
@permission_popup
def save_sequences(test_seq_df, command_df, data_folder, partial=False):
    """Save test_seq_df and command_df to correct locations"""
    # save to appdata directory
    test_seq_df.to_csv(APPDATA_DIR.joinpath('test-sequence.csv'), index=False)
    command_df.to_csv(APPDATA_DIR.joinpath('command-sequence.csv'), index=False, header=False)
    # also save within the data_folder
    if partial:
        # also save to Partial subdirectory for records
        partial_dir = Path(data_folder).joinpath('Partial')
        partial_dir.mkdir(exist_ok=True)
        today = datetime.today().strftime('%Y-%h-%d-%H-%M')
        test_seq_df.to_csv(partial_dir.joinpath(f'partial-test-sequence-{today}.csv'), index=False)
        command_df.to_csv(partial_dir.joinpath(f'partial-command-sequence-{today}.csv'), index=False, header=False)
    else:
        test_seq_df.to_csv(data_folder.joinpath('test-sequence.csv'), index=False)
        command_df.to_csv(data_folder.joinpath('command-sequence.csv'), index=False, header=False)
    