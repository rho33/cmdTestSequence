import pandas as pd


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
    'sdr': 'IEC_Broadcast_HD_5994p_SDR_HEVC_AAC.mp4',
    'clasp_hdr': 'IEC_Broadcast_HD_5994p_HDR10_HEVC_AAC.mp4',
    'dots': 'Dots.mp4',
    'lum_sdr': 'Lum.mp4',
    'default_level': 'Default Level',
    'lowest_level': 'Lowest Level',
    'backlight': 'Backlight Setting',
    'oob': 'Default Out of Box Setting',
    'off': 'Off',
    'on': 'On',
    'no': 'No',
    'yes': 'Yes',
    'ccf': 'CCF.mp4',
    'lan': 'LAN',
    'wan': 'WAN'
}


STAB_MAX_ITER = 6

# todo: manual sequence custom message
def display_row_settings(row):
    """Create test condition/settings portion of test prompt."""
    non_setting_cols = ['special_commands', 'tag', 'test_name', 'test_time', 'lan', 'wan']
    display_row = row.drop(non_setting_cols).dropna().rename(RENAME_DICT).replace(RENAME_DICT)
    s = '-'*80
    s += '\\nEnsure that the current test conditions are:\\n\\n'
    for setting, val in zip(display_row.index, display_row):
        if setting == 'Illuminance Level (Lux)':
            val = int(val)
        s += f'    {setting} - {val}'
        if setting == RENAME_DICT['mdd']:
            s += ' (if applicable)'
        s += '\\n'
    return s


def message_heading(current_row):
    """Create message heading portion of test prompt."""
    message = f'Test Name: {current_row["test_name"]}\\nTest Tag: {current_row["tag"]}\\n'
    if pd.notnull(current_row['test_time']):
        message += f'Test Time (seconds): {int(current_row["test_time"])}\\n\\n'
    return message


def message_instructions(current_row, previous_row=None, extra=None, countdown=True):
    """Create user instruction portion of test prompt."""
    setting_titles = {
        'mdd': 'motion detection dimming (MDD)',
        'abc': 'automatic brightness control (ABC)',
        'qs': 'quickstart (QS)',
        'preset_picture': 'preset picture',
    }
    test_clip = RENAME_DICT.get(current_row['video'], current_row['video'])
    message = '-' * 80
    message += '\\nInstructions:\\n\\n'
    if extra:
        message += extra
    if previous_row is not None:
        changes = current_row[(current_row != previous_row) & pd.notnull(current_row)]
        for col, change_val in changes.iteritems():
            if col in setting_titles.keys():
                message += f'* Change the {setting_titles[col]} setting to {change_val}'
                if col == 'mdd':
                    message += ' (if applicable)'
                message += '\\n'
            elif col == 'lux':
                message += f'* Adjust the illuminance level to {int(change_val)} lux\\n'
            elif col == 'video':
                message += f'* Change the video clip to {test_clip}\\n'
            elif col == 'backlight' and change_val == 'lowest_level':
                message += '* Lower the backlight setting to the lowest possible level and record this level.\\n'
    if countdown:
        message += f'* When ready begin the {test_clip} clip and press the OK button precisely when the test clip content begins at the end of the countdown. The accuracy of the test depends on pressing the OK button at the correct time.\\n\\n'
    return message


def user_message(i, test_seq_df):
    """Create standard test prompt"""
    previous_row = test_seq_df.iloc[i - 1]
    current_row = test_seq_df.iloc[i]
    message = message_heading(current_row)
    message += message_instructions(current_row, previous_row)
    message += display_row_settings(current_row)
    return message


def waketime_message_start(row):
    """Create waketime test prompt."""
    message = message_heading(row)
    message += '-' * 80
    message += '\\nInstructions:\\n\\n'
    message += '* Now that the standby test is complete measure wake time.\\n'
    message += '* Use the Remote Start feature to wake the TV; press OK as soon as you trigger waking by remote start.\\n'
    message += '* A new message will appear asking you to press another button as soon as you see the HDMI video stream displayed.'
    return message


# Scecond (finishing) test prompt for waketime tests
WT_MESSAGE2 = "As soon as you see the HDMI video stream displayed press the OK button. This can happen very quickly."


def lum_profile_message(row):
    """Create lum profile test prompt."""
    message = message_heading(row)
    extra = '* Next we will capture the luminance profile of the TV.\\n'
    message += message_instructions(row, extra=extra, countdown=False)
    test_clip = RENAME_DICT.get(row['video'], row['video'])
    message += f'* When ready begin the {test_clip} clip and press the OK button when the screen is completely white and there is no overlay.\\n\\n'
    message += display_row_settings(row)
    return message


def stabilization_message(row):
    """Create stabilization test(s) prompt."""
    message = message_heading(row)
    extra = f'This test repeats until TV power output is stable or until {STAB_MAX_ITER} iterations is reached (minimum 2 iterations).\\n'
    extra = f"This step stabilizes the TV by comparing the first 5 mins of consecutive runs of {RENAME_DICT['sdr']}. When the average power of a run is within 2% of the previous run or after 6 runs this step will end.\\n"
    message += message_instructions(row, extra=extra)
    message += display_row_settings(row)
    return message


def standby_message(row):
    """Create standby test prompt."""

    message = message_heading(row)
    message += '-' * 80
    message += '\\nInstructions:\\n\\n'
    # message += f'* The next test will be a standby test.\\n'
    message += '* Remove the USB stick from the TV\\n'
    if 'echo' in row['test_name']:
        message += '* Connect the TV to the Amazon Echo\\n'
    if 'google' in row['test_name']:
        message += '* Connect the TV to the Google Home\\n'
    if 'qs' in row.index:
        message += f'* Ensure that QuckStart is set to {RENAME_DICT[row["qs"]]}'
        # if row['qs']=='off':
        #     message+= ' (if applicable)'
        message += '.\\n'
    message += '* If not enabled configure the TV to wake via Remote Start.\\n'
    message += '* Play dynamic video by HDMI.\\n'
    message += "* Power down the TV using the remote and press the OK button as soon as the TV powers off."
    return message


def screen_config_message(row):
    """Create screen_config test prompt."""
    message = message_heading(row)
    extra = '* Next we will configure the camera for the remaining tests.\\n'
    message += message_instructions(row, extra=extra, countdown=False)
    message += "Press OK when the clip is on the screen with no overlay\\n\\n"
    message += display_row_settings(row)
    return message


def create_command_df(test_seq_df):
    """Create dataframe that will eventually to be saved to to command-sequence.csv and fed to Labview."""
    
    # command_rows is a list of tuples containing data to be turned into dataframe (each tuple is a row)
    # command_rows always starts with these 6 1 column rows
    command_rows = [(i,) for i in ['#Config', 'Remote name', 'IR Delay (ms)', 'Macro File', '', '#Sequence']]
    # for each test (row) in test_seq_df create the appropriate rows in command_rows
    for i, row in test_seq_df.iterrows():
        command_rows.append(('tag', row['tag']))
        if 'waketime' in row['test_name']:
            command_rows.extend([
                ('user_command', waketime_message_start(row)),
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
            command_rows.append(('user_stabilization', stabilization_message(row), 300, STAB_MAX_ITER))
        elif 'ccf' in row['test_name']:
            before_ccf_msg = 'If the TV has Local Dimming disable it for the color correction factor step; then click OK'
            command_rows.append(('user_command', before_ccf_msg))
        else:
            command_rows.append(('user_command', user_message(i, test_seq_df)))

        if not pd.isnull(row['test_time']):
            command_rows.append(('wait', row['test_time']))

        if not pd.isnull(row['special_commands']):
            for special_command in row['special_commands'].split(','):
                
                
                command_type, command = special_command.split(':')
                if command_type == 'camera_ccf':
                    command_rows.append((command_type, command.strip(), 9))
                else:
                    command_rows.append((command_type, command.strip()))
        if 'ccf' in row['test_name']:
            after_ccf_msg = 'If you changed Local Dimming prior to determining the color correction factor return it to its default setting for the rest of the test; then click OK'
            command_rows.append(('user_command', after_ccf_msg))

    command_df = pd.DataFrame(data=command_rows)
    command_df.columns = ['command_type', 'command', 'stab_wait', 'max_stab'][:command_df.shape[1]]
    return command_df
