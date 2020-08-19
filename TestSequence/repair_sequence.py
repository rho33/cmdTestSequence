"""Usage:
repair_sequence.exe <data_folder> <test_tags>...
"""
import sys
from docopt import docopt
from pathlib import Path
import numpy as np
import pandas as pd
import sequence as ts
import command_sequence as cs
sys.path.append('..')
from filefuncs import get_paths
import logfuncs as lf


def get_test_order(og_test_seq_df, tags):
    tests = ts.get_tests()
    og_test_seq_df['generic_pps'] = og_test_seq_df['test_name'].apply(lambda test: tests[test]['preset_picture'])
    tag_df = og_test_seq_df[og_test_seq_df['tag'].isin(tags)]
    stab_idx = og_test_seq_df.query("test_name=='stabilization'").index[0]
    setup_df = og_test_seq_df[(og_test_seq_df.index <= stab_idx)
                              & (og_test_seq_df['test_name'] != 'lum_profile')
                              & (og_test_seq_df['generic_pps'].isin(tag_df['generic_pps'].unique()))
    ]
    test_order = list(pd.concat([setup_df, tag_df])['test_name'])
    return test_order


def recreate_rename_pps(test_seq_df, tests):
    test_seq_df['generic_pps'] = test_seq_df['test_name'].apply(lambda test: tests[test]['preset_picture'])
    df = test_seq_df.dropna(subset=['preset_picture'])
    rename_pps = dict(zip(df['generic_pps'], df['preset_picture']))
    return rename_pps


def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'repair-sequence.log')

    repair_folder = data_folder.joinpath('Repair')
    repair_folder.mkdir(exist_ok=True)
    
    tags = docopt_args['<test_tags>']
    paths = get_paths(data_folder)
    logger.info(paths)
    
    og_test_seq_df = pd.read_csv(paths['test_seq'])
    test_order = get_test_order(og_test_seq_df, tags)
    
    rename_pps = recreate_rename_pps(og_test_seq_df, ts.get_tests())
    qson = (og_test_seq_df['qs'] == 'on').any()
    test_seq_df = ts.create_test_seq_df(test_order, rename_pps, qson)
    test_seq_df.index = range(len(test_seq_df))
    tag_to_name = dict(zip(og_test_seq_df['tag'], og_test_seq_df['test_name']))
    repair_tags = {tag_to_name[int(tag)]: f"{tag} repair" for tag in tags}
    test_seq_df['tag'] = np.where(test_seq_df['test_name'].isin(repair_tags),
                                  test_seq_df['test_name'].apply(repair_tags.get),
                                  test_seq_df['tag'])
    logger.info('\n' + test_seq_df.to_string())
    
    command_df = cs.create_command_df(test_seq_df)
    ts.save_sequences(test_seq_df, command_df, data_folder, repair=True)
    
    # todo: call do_repair
    

if __name__ == '__main__':
    main()