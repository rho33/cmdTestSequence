"""Usage:
partial_sequence.exe  <data_folder> <tags>... [options]

Arguments:
  data_folder       folder with test data
  tags              list of tests to include in partial sequence
Options:
  -h --help
"""
import sys
import pandas as pd
import core.logfuncs as lf
import core.filefuncs as ff
import core.sequence.command_sequence as cs


def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'compliance_report.log')
    paths = ff.get_paths(data_folder)
    test_seq_df = pd.read_csv(paths['test_seq'])
    tags = [int(i) for i in docopt_args['<tags>']]
    mask = (test_seq_df['test_name'].isin(['screen_config', 'stabilization'])) | (test_seq_df['tag'].isin(tags))
    
    if paths['ccf'] is None:
        mask = mask | (test_seq_df['test_name'].apply(lambda name: 'ccf' in name))
    
    partial_test_seq_df = test_seq_df[mask].reset_index()
    partial_test_seq_df.to_csv('partial-ts.csv', index=False)
    command_df = cs.create_command_df(partial_test_seq_df)
    
    command_df.to_csv('partial-cs.csv', index=False, header=False)


if __name__ == '__main__':
    main()