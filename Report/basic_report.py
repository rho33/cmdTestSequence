"""Usage:
basic_report.exe  <data_folder> [options]

Arguments:
  data_folder       folder with test data, also destination folder

Options:
  -h --help
"""
import sys
sys.path.append('..')
from report_data import get_report_data, check_report_data
from report import add_test_results_plots, ISection, build_report, add_test_specs, add_test_results_table
import logfuncs as lf
import filefuncs as ff


def make_basic_report(report_data):
    report = ISection(name='report')
    report = add_test_specs(report, **report_data)
    report = add_test_results_table(report, **report_data)
    report = add_test_results_plots(report, **report_data)
    report_name = f'basic-report.pdf'
    build_report(report, report_name, **report_data)
    
    
def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'basic_report.log')
    paths = ff.get_paths(data_folder)
    report_data = get_report_data(paths, data_folder, docopt_args)
    expected_data = [
        'data_folder',
        'merged_df',
        'rsdf',
        'test_specs_df'
    ]
    check_report_data(report_data, expected_data)
    make_basic_report(report_data)
    
    
if __name__ == '__main__':
    main()