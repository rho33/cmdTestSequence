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
  --hdrabc      test abc with hdr
  --brabc       test abc with brightest pps
  --qson        standby test with qs on
  --qs          tv has quickstart
"""
from docopt import docopt
import pandas as pd
import sys
from pathlib import Path

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
    test_order += abc_br_tests[docopt_args['--brabc']]
    if docopt_args['--hdr']:
        test_order += abc_hdr_tests[docopt_args['--hdrabc']]
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


def user_message(i, test_seq_df):
    previous_row = test_seq_df.iloc[i - 1]
    current_row = test_seq_df.iloc[i]
    changes = current_row[current_row == previous_row]

    setting_titles = {
        'mdd': 'motion detection dimming (MDD)',
        'abc': 'automatic brightness control (ABC)',
        'qs': 'quickstart (QS)',
        'preset_picture': 'preset picture'
    }

    s = ''
    for col, change_val in changes.iteritems():
        if col in ['preset_picture', 'abc', 'mdd', 'qs']:
            s += f'Change the {setting_titles[col]} setting to {change_val}\\n'
        elif col == 'lux':
            s += f'Adjust the illuminance level to {change_val} lux\\n'
        elif col == 'video':
            s += f'Change the video clip to {RENAME_DICT[change_val]}\\n'
        elif col == 'backlight' and change_val == 'lowest_level':
            s += 'Lower the backlight setting to the lowest possible level'

    s += '\\nThe conditions for the current test should be:\\n'
    s += current_row.dropna().rename(RENAME_DICT).replace(RENAME_DICT).to_string().replace('\n', '\\n')
    s += '\\n When ready, begin the test clip and press the button below when the countdown timer reaches 0.'
    return s


WT_MESSAGE1 = "Now that the standby test is complete we are going to measure wake time. Press the button below at" \
    "the same time as you press the power button to turn on your television. You will then see another button to press. As soon as the TV has become responsive to input, press this button."


WT_MESSAGE2 = "As soon as the TV becomes responsive to input, press the button below."


def lum_profile_message(row):
    s = 'Next we will capture the luminance profile of the TV. Change the video clip to SDR Luminance Profile\\n'
    s += '\\nThe conditions for this test should be:\\n'
    s += row.dropna().rename(RENAME_DICT).replace(RENAME_DICT).to_string().replace('\n', '\\n')
    s += '\\n When ready, begin the test clip and press the button below when the countdown timer reaches 0.'
    return s


def stabilization_message(row):
    s = 'The following test will be a stabilization test. We will run these until we get two consecutive tests with average power within 2% of each other.\\n'
    s += '\\nThe conditions for this test should be:\\n'
    s += row.dropna().rename(RENAME_DICT).replace(RENAME_DICT).to_string().replace('\n', '\\n')
    s += '\\n When ready, begin the test clip and press the button below when the countdown timer reaches 0.'
    return s


def standby_message(row):
    message = f'Test Name: {row["test_name"]}\\n'
    message += f'The next test will be a standby test. It will last {row["test_time"]/60} minutes \\n'
    if 'echo' in row['test_name']:
        message += 'Connect the TV to the Amazon Echo\\n'
    if 'google' in row['test_name']:
        message += 'Connect the TV to the Google Home\\n'
    if 'qs' in row.index:
        message += f'Ensure that QuckStart is set to {RENAME_DICT[row["qs"]]}.\\n'
    message += "Power down the TV using the remote and press the button below to begin test."
    return message


def screen_config_message(row):
    s = 'Next we will configure the camera for the remaining tests.\\n'
    s += '\\nThe conditions for this test should be:\\n'
    s += row.dropna().rename(RENAME_DICT).replace(RENAME_DICT).to_string().replace('\n', '\\n')
    s += '\\n When ready, begin the test clip and press the button below when the countdown timer reaches 0.'
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


def main():
    docopt_args = docopt(__doc__)
    test_order = get_test_order(docopt_args)
    tests = get_tests()
    test_seq_df = create_test_seq_df(tests, test_order, docopt_args)
    test_seq_df.to_csv("test-sequence.csv", index=False)
    command_df = create_command_df(test_seq_df)
    command_df.to_csv('command-sequence.csv', index=False, header=False)


if __name__ == '__main__':
    main()
