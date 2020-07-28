from itertools import combinations
from docopt import docopt
import pandas as pd
import tv_test_sequence as tts


def get_arg_seqs():
    """get all valid argument combinations/sequences"""
    options = {
        'h': ['--hdr', 'hdr standard'],
        'qn': ['--qs', '8'],
        'qf': ['--qs', '11'],
        'da': ['--defabc'],
        'ba': ['--brabc'],
        'ha': ['--hdrabc']
    }
    seqs = {'base': ['sample model', 'standard', 'dynamic']}
    for i in range(1, len(options) + 1):
        for key_tup in combinations(options.keys(), i):
            if 'qn' in key_tup and 'qf' in key_tup:
                pass
            else:
                seq_key = '_'.join(list(key_tup))
                seq = [] + seqs['base']
                for opt_key in key_tup:
                    seq += options[opt_key]
                seqs[seq_key] = seq

    return seqs


def test_docopt():
    arg_seqs = get_arg_seqs()
    for key, seq in arg_seqs.items():
        docopt_args = docopt(tts.__doc__, argv=seq)
        assert isinstance(docopt_args, dict)
        expected_types = {
            '--brabc': [bool],
            '--defabc': [bool],
            '--hdr': [type(None), str],
            '--hdrabc': [bool],
            '--help': [bool],
            '--qs': [type(None), str],
            '<brightest_pps>': [str],
            '<default_pps>': [str],
            '<model>': [str]
        }
        assert docopt_args.keys() == expected_types.keys()
        for arg, val in docopt_args.items():
            assert type(val) in expected_types[arg]

    args = ['some model', 'standard', 'dynamic', '--hdr', 'hdr standard']
    docopt_args = docopt(tts.__doc__, argv=args)
    expected_args = {
        '--brabc': False,
        '--defabc': False,
        '--hdr': 'hdr standard',
        '--hdrabc': False,
        '--help': False,
        '--qs': None,
        '<brightest_pps>': 'dynamic',
        '<default_pps>': 'standard',
        '<model>': 'some model'
    }
    assert docopt_args == expected_args


def test_get_test_order():
    docopt_args = {
        '--brabc': None,
        '--defabc': None,
        '--hdr': 'hdr standard',
        '--hdrabc': None,
        '--help': False,
        '--qs': '8',
        '<brightest_pps>': 'dynamic',
        '<default_pps>': 'standard',
        '<model>': 'some model'
    }
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
    test_order = tts.get_test_order(docopt_args)
    assert test_order == expected_test_order
    docopt_args = {
        '--brabc': True,
        '--defabc': True,
        '--hdr': 'hdr standard',
        '--hdrabc': True,
        '--help': False,
        '--qs': '8',
        '<brightest_pps>': 'dynamic',
        '<default_pps>': 'standard',
        '<model>': 'some model'
    }
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
        'default_100',
        'default_35',
        'default_12',
        'default_3',
        'brightest',
        'brightest_100',
        'brightest_35',
        'brightest_12',
        'brightest_3',
        'hdr',
        'hdr_100',
        'hdr_35',
        'hdr_12',
        'hdr_3'
    ]
    test_order = tts.get_test_order(docopt_args)
    assert test_order == expected_test_order


def test_get_tests():
    tests = tts.get_tests()
    assert isinstance(tests, dict)
    for test_name, details in tests.items():
        assert test_name == details['test_name']


def test_create_test_seq_df():
    arg_seqs = get_arg_seqs()
    for _, seq in arg_seqs.items():
        docopt_args = docopt(tts.__doc__, argv=seq)
        test_order = tts.get_test_order(docopt_args)
        tests = tts.get_tests()

        test_seq_df = tts.create_test_seq_df(tests, test_order, docopt_args)
        assert isinstance(test_seq_df, pd.DataFrame)
        assert len(test_seq_df) >= 13
        min_cols  = ['tag','test_name','test_time','video','preset_picture','backlight', 'special_commands']
        for col in min_cols:
            assert col in test_seq_df.columns
        max_cols = ['tag','test_name','test_time','video','preset_picture','backlight', 'special_commands', 'mdd',
                    'abc', 'lux', 'qs']
        for col in test_seq_df.columns:
            assert col in max_cols
        expected_col_hasna = {
            'tag': False,
            'test_time': True,
            'test_name': False,
            'video': True,
            'preset_picture': True,
            'backlight': True,
            'special_commands': True,
            'mdd': True,
            'abc': True,
            'lux': True,
            'qs': True,
        }
        actual_col_hasna = test_seq_df.isna().any().to_dict()
        for col, hasna in actual_col_hasna.items():
            assert hasna == expected_col_hasna[col]


def test_messages():
    args = ['some model', 'standard', 'dynamic', '--hdr', 'hdr standard']
    docopt_args = docopt(tts.__doc__, argv=args)
    test_order = tts.get_test_order(docopt_args)
    tests = tts.get_tests()
    test_seq_df = tts.create_test_seq_df(tests, test_order, docopt_args)
    for i, row in test_seq_df.iterrows():
        print(i)
        if 'stabilization' in row['test_name']:
            assert isinstance(tts.stabilization_message(row), str)
        elif 'lum' in row['test_name']:
            assert isinstance(tts.lum_profile_message(row), str)
        elif 'standby' in row['test_name']:
            assert isinstance(tts.standby_message(row), str)
        elif 'screen' in row['test_name']:
            assert isinstance(tts.screen_config_message(row), str)
        elif 'waketime' not in row['test_name']:
            assert isinstance(tts.user_message(i, test_seq_df), str)


def test_create_command_df():
    arg_seqs = get_arg_seqs()
    for _, seq in arg_seqs.items():
        docopt_args = docopt(tts.__doc__, argv=seq)
        test_order = tts.get_test_order(docopt_args)
        tests = tts.get_tests()

        test_seq_df = tts.create_test_seq_df(tests, test_order, docopt_args)
        command_df = tts.create_command_df(test_seq_df)
        assert isinstance(command_df, pd.DataFrame)
        assert len(command_df) > 10
        command_types = ['#Config', 'Remote name', 'IR Delay (ms)', 'Macro File', '#Sequence','tag', 'wait',
                         'user_command','user_stabilization', '', 'screen_config', 'lum_profile']
        for i, val in command_df['command_type'].dropna().iteritems():
            assert val in command_types

