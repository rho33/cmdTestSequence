from docopt import docopt
import pandas as pd
import tv_test_sequence as tts

def test_docopt():
    args = ['some model', 'standard', 'dynamic', '--mdd', '--hdr', 'hdr standard']
    docopt_args = docopt(tts.__doc__, argv=args)
    expected_args = {
        '--brabc': False,
        '--defabc': None,
        '--hdr': 'hdr standard',
        '--hdrabc': False,
        '--help': False,
        '--mdd': True,
        '--qs': False,
        '--qson': False,
        '<brightest_pps>': 'dynamic',
        '<default_pps>': 'standard',
        '<model>': 'some model'
    }
    assert docopt_args == expected_args


def test_get_test_order():
    docopt_args = {
        '--brabc': False,
        '--defabc': False,
        '--hdr': 'hdr standard',
        '--hdrabc': False,
        '--help': False,
        '--mdd': True,
        '--qs': False,
        '--qson': False,
        '<brightest_pps>': 'dynamic',
        '<default_pps>': 'standard',
        '<model>': 'some model'
    }
    test_order = tts.get_test_order(docopt_args)
    expected_test_order = [
        'standby',
        'waketime',
        'standby_echo',
        'echo_waketime',
        'standby_google',
        'google_waketime',
        'screen_config',
        'lum_profile',
        'stabilization',
        'default',
        'default_low_backlight',
        'brightest',
        'brightest_low_backlight',
        'hdr',
        'hdr_low_backlight'
    ]
    assert test_order == expected_test_order


def test_get_tests():
    assert isinstance(tts.get_tests(), dict)


def test_create_test_seq_df():
    args = ['some model', 'standard', 'dynamic', '--mdd', '--hdr', 'hdr standard']
    docopt_args = docopt(tts.__doc__, argv=args)
    test_order = tts.get_test_order(docopt_args)
    tests = tts.get_tests()

    test_seq_df = tts.create_test_seq_df(tests, test_order, docopt_args)
    assert isinstance(test_seq_df, pd.DataFrame)


def test_messages():
    args = ['some model', 'standard', 'dynamic', '--mdd', '--hdr', 'hdr standard']
    docopt_args = docopt(tts.__doc__, argv=args)
    test_order = tts.get_test_order(docopt_args)
    tests = tts.get_tests()
    test_seq_df = tts.create_test_seq_df(tests, test_order, docopt_args)
    for i, row in test_seq_df.iterrows():
        assert isinstance(tts.user_message(i, test_seq_df), str)
        assert isinstance(tts.lum_profile_message(row), str)
        assert isinstance(tts.stabilization_message(row), str)
        assert isinstance(tts.standby_message(row), str)
        assert isinstance(tts.screen_config_message(row), str)


def test_create_command_df():
    args = ['some model', 'standard', 'dynamic', '--mdd', '--hdr', 'hdr standard']
    docopt_args = docopt(tts.__doc__, argv=args)
    test_order = tts.get_test_order(docopt_args)
    tests = tts.get_tests()

    test_seq_df = tts.create_test_seq_df(tests, test_order, docopt_args)
    command_df = tts.create_command_df(test_seq_df)
    assert isinstance(command_df, pd.DataFrame)

