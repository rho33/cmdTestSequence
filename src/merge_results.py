"""
Usage:
merge_results.exe <data_folder> [options]

Arguments:
  data_folder       folder with test data
  
Options:
  -h --help
"""
import core.logfuncs as lf
import core.filefuncs as ff
from core.report.report_data import get_merged_df

def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'merge_results.log')
    paths = ff.get_paths(data_folder)
    get_merged_df(paths, data_folder)


if __name__ == '__main__':
    main()