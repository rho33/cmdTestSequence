"""Usage:
manual_sequence.exe <data_folder>
"""
import sys
from pathlib import Path
import pandas as pd
from sequence import save_sequences
from command_sequence import create_command_df
sys.path.append('..')
import logfuncs as lf

# todo: manual sequence custom message (probably in command_sequence create_command_df function)
def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'manual-sequence.log')
    test_seq_df = pd.read_csv(Path(sys.path[0]).joinpath('manual-sequence.csv'))
    command_df = create_command_df(test_seq_df)
    save_sequences(test_seq_df, command_df, data_folder)
    pass


if __name__ == '__main__':
    main()
