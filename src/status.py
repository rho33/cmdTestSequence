"""
Usage:
status.exe <data_folder> [options]

Arguments:
  data_folder       folder with test data, also destination folder

Options:
  -h --help
"""
import pandas as pd
import core.report.report_data as rd
import core.logfuncs as lf
import core.filefuncs as ff

    
def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'test_status.log')
    paths = ff.get_paths(data_folder)

    test_seq_df = pd.read_csv(paths['test_seq'])
    merged_df = rd.get_merged_df(test_seq_df, paths, data_folder)
    
    rd.get_status_df.__wrapped__(test_seq_df, merged_df, paths, data_folder)
    
    
if __name__ == '__main__':
    main()