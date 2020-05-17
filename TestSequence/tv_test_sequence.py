"""Usage:
tv_test_sequence.exe  <model> <default_pps> <brightest_pps> [options]

Arguments:
  model             tv model code
  default_pps       name of default preset picture setting
  brightest_pps     name of brightest preset picture setting

Options:
  -h --help
  --defabc=pps  specify default abc on preset picture setting for testing
  --mdd         tv has mdd
  --hdr=pps     specify hdr preset picture setting for testing
  --hdrabc=pps  specify hdr preset picture setting for hdr abc testing
  --brabc=pps   specify "brightest" pps for testing with abc on
  --qson        standby test with qs on
  --qs          tv has quickstart
"""
from docopt import docopt
import pandas as pd
import sys
import shutil
from pathlib import Path
from datetime import datetime

RENAME_DICT = {
    'tag': 'Test Number',
    'test_name': 'Test Name',
    'test_time': 'Test Duration (Seconds)',
    'video': 'Video Clip',
    'preset_picture': 'Preset Picture Setting',
    'abc': 'Automatic Brightness Control (ABC)',
    'lux': 'Illuminance Level (Lux)',
    'mdd': 'Motion Detection Dimming (MDD)',
    'qs': 'QuickStart',
    'sdr': 'IEC SDR',
    'clasp_hdr': 'CLASP HDR',
    'dots': 'Dots Pattern',
    'lum_sdr': 'Luminance Profile',
    'default_level': 'Default Level',
    'lowest_level': 'Lowest Level',
    'backlight': 'Backlight Setting',
    'oob': 'Default Out of Box Setting',
    'off': 'Off',
    'on': 'On',
}

def get_test_order(docopt_args):
    """Determine test order from option arguments."""
    abc_def_tests = {
        True: ['default', 'default_100', 'default_35', 'default_12', 'default_3'],
        False: ['default', 'default_low_backlight']
    }
    abc_br_tests = {
        True: ['brightest', 'brightest_100', 'brightest_35', 'brightest_12', 'brightest_3'],
        False: ['brightest', 'brightest_low_backlight']
    }
    abc_hdr_tests = {
        True: ['hdr', 'hdr_100', 'hdr_35', 'hdr_12', 'hdr_3'],
        False: ['hdr', 'hdr_low_backlight']
    }
    test_order = [
        'standby',
        'waketime',
        'standby_echo',
        'echo_waketime',
        'standby_google',
        'google_waketime',
        'screen_config',
        'lum_profile',
        'stabilization',
    ]
    test_order += abc_def_tests[bool(docopt_args['--defabc'])]
    test_order += abc_br_tests[bool(docopt_args['--brabc'])]
    if docopt_args['--hdr']:
        test_order += abc_hdr_tests[bool(docopt_args['--hdrabc'])]
    return test_order


def get_tests():
    """Construct dictionary of all possible tests from csv file."""
    path = Path(sys.path[0]).joinpath('test-details.csv')
    df = pd.read_csv(path).T
    df.columns = df.iloc[0]
    tests = df.to_dict()
    return tests


def create_test_seq_df(tests, test_order, docopt_args):
    """Construct test sequence DataFrame"""
    columns = ['test_name', 'test_time', 'video', 'preset_picture', 'abc', 'lux', 'mdd', 'qs']
    df = pd.DataFrame(columns=columns)
    for test in test_order:
        df = df.append(tests[test], ignore_index=True)

    if docopt_args['--qson']:
        df['qs'] = df['qs'].replace({'off': 'on'})

    if not docopt_args['--defabc'] and not docopt_args['--brabc'] and not docopt_args['--hdrabc']:
        del df['abc'], df['lux']
    if not docopt_args['--mdd']:
        del df['mdd']
    if not docopt_args['--qs']:
        del df['qs']

    rename_pps = {
        'default': docopt_args['<default_pps>'],
        'brightest': docopt_args['<brightest_pps>'],
        'hdr_default': docopt_args['--hdr'],
        'abc_default': docopt_args['--defabc']
    }
    df['preset_picture'] = df['preset_picture'].replace(rename_pps)

    df.index.name = 'tag'
    return df.reset_index()


def display_row_settings(row):
    non_setting_cols = ['special_commands', 'tag', 'test_name', 'test_time']
    display_row = row.drop(non_setting_cols).dropna().rename(RENAME_DICT).replace(RENAME_DICT)
    s = ''
    for setting, val in zip(display_row.index, display_row):
        s += f'{setting} - {val}\\n'
    return s


def user_message(i, test_seq_df):
    previous_row = test_seq_df.iloc[i - 1]
    current_row = test_seq_df.iloc[i]
    changes = current_row[(current_row != previous_row) & pd.notnull(current_row)]

    setting_titles = {
        'mdd': 'motion detection dimming (MDD)',
        'abc': 'automatic brightness control (ABC)',
        'qs': 'quickstart (QS)',
        'preset_picture': 'preset picture',
    }

    message = f'Test Name: {current_row["test_name"]}\\nTest Tag: {current_row["tag"]}\\nTest Time (seconds): {int(current_row["test_time"])}\\n\\n'
    for col, change_val in changes.iteritems():
        if col in setting_titles.keys():
            message += f'Change the {setting_titles[col]} setting to {change_val}\\n'
        elif col == 'lux':
            message += f'Adjust the illuminance level to {change_val} lux\\n'
        elif col == 'video':
            message += f'Change the video clip to {RENAME_DICT[change_val]}\\n'
        elif col == 'backlight' and change_val == 'lowest_level':
            message += 'Lower the backlight setting to the lowest possible level\\n'

    message += '\\nThe conditions for the current test should be:\\n'
    message += display_row_settings(current_row)
    message += '\\n When ready begin the test clip and press the OK button when the countdown timer reaches 0.'
    return message


WT_MESSAGE1 = "Now that the standby test is complete we are going to measure wake time. Press the OK button at " \
    "the same time as you press the power button to turn on the television. " \
    "A new message will appear asking you to press another button as soon as the TV has become responsive to input."


WT_MESSAGE2 = "As soon as the TV becomes responsive to input press the OK button."


def lum_profile_message(row):
    message = f'Test Name: {row["test_name"]}\\nTest Tag: {row["tag"]}\\n\\n'
    message += 'Next we will capture the luminance profile of the TV.\\nChange the video clip to SDR Luminance Profile\\n'
    message += '\\nThe conditions for this test should be:\\n'
    message += display_row_settings(row)
    message += '\\n\\n When ready begin the test clip and press the OK button when the countdown timer reaches 0.'
    return message


def stabilization_message(row):
    message = f'Test Name: {row["test_name"]}\\nTest Tag: {row["tag"]}\\n\\n'
    message += 'The following test will be a stabilization test. We will run these until we get two consecutive tests with average power within 2% of each other.\\n'
    message += '\\nThe conditions for this test should be:\\n'
    message += display_row_settings(row)
    message += '\\n\\n When ready begin the test clip and press the OK button when the countdown timer reaches 0.\\n'
    return message


def standby_message(row):

    message = f'Test Name: {row["test_name"]}\\nTest Time (seconds): {int(row["test_time"])}\\n\\n'
    message += f'The next test will be a standby test\\n'
    if 'echo' in row['test_name']:
        message += 'Connect the TV to the Amazon Echo\\n'
    if 'google' in row['test_name']:
        message += 'Connect the TV to the Google Home\\n'
    if 'qs' in row.index:
        message += f'Ensure that QuckStart is set to {RENAME_DICT[row["qs"]]}.\\n'
    message += "Power down the TV using the remote and press the OK button to begin test."
    return message


def screen_config_message(row):
    s = 'Next we will configure the camera for the remaining tests.\\n'
    s += '\\nThe conditions for this test should be:\\n'
    s += display_row_settings(row)
    s += '\\n\\n When ready begin the test clip and press the OK button when the countdown timer reaches 0.'
    return s


def create_command_df(test_seq_df):
    command_rows = [(i,) for i in ['#Config', 'Remote name', 'IR Delay (ms)', 'Macro File', '', '#Sequence']]
    for i, row in test_seq_df.iterrows():
        command_rows.append(('tag', row['tag']))
        if 'waketime' in row['test_name']:
            command_rows.extend([
                ('user_command', WT_MESSAGE1),
                ('tag', row['tag'] + .1),
                ('user_command', WT_MESSAGE2)
            ])
        elif 'config' in row['test_name']:
            command_rows.append(('user_command', screen_config_message(row)))
        elif 'lum_profile' in row['test_name']:
            command_rows.append(('user_command', lum_profile_message(row)))
        elif 'standby' in row['test_name']:
            command_rows.append(('user_command', standby_message(row)))
        elif 'stabilization' in row['test_name']:
            command_rows.append(('user_stabilization', stabilization_message(row), 600, 6))
        else:
            command_rows.append(('user_command', user_message(i, test_seq_df)))

        if not pd.isnull(row['test_time']):
            command_rows.append(('wait', row['test_time']))

        if not pd.isnull(row['special_commands']):
            for special_command in row['special_commands'].split(','):
                command_type, command = special_command.split(':')
                command_rows.append((command_type, command.strip()))

    command_df = pd.DataFrame(data=command_rows)
    command_df.columns = ['command_type', 'command', 'stab_wait', 'max_stab'][:command_df.shape[1]]
    return command_df


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


def main():
    docopt_args = docopt(__doc__)
    test_order = get_test_order(docopt_args)
    tests = get_tests()
    test_seq_df = create_test_seq_df(tests, test_order, docopt_args)
    command_df = create_command_df(test_seq_df)

    results_dir = Path(docopt_args['<model>'])
    results_dir.mkdir(exist_ok=True)

    filename = 'test-sequence.csv'
    test_seq_df.to_csv(filename, index=False)
    results_filepath = results_dir.joinpath(filename)
    if results_filepath.exists():
        archive(results_filepath, date=True)
    shutil.copy(filename, results_filepath)

    filename = 'command-sequence.csv'
    command_df.to_csv(filename, index=False, header=False)
    results_filepath = results_dir.joinpath(filename)
    if results_filepath.exists():
        archive(results_filepath, date=True)
    shutil.copy(filename, results_filepath)


if __name__ == '__main__':
    main()
