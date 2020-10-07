"""Usage:
compliance_report.exe  <data_folder> [options]

Arguments:
  data_folder       folder with test data, also destination folder

Options:
  -h --help
"""
import sys
sys.path.append('..')
from report_data import get_report_data, check_report_data
from report import add_compliance_section, ISection, build_report, add_test_specs
import logfuncs as lf
import filefuncs as ff

def make_compliance_report(report_data):
    report = ISection(name='report')
    report = add_test_specs(report, **report_data)
    report = add_compliance_section(report, **report_data)
    report_name = f'compliance-report.pdf'
    build_report(report, report_name, **report_data)
            
            
def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'compliance_report.log')
    paths = ff.get_paths(data_folder)
    report_data = get_report_data(paths, data_folder, docopt_args)
    expected_data = [
        'data_folder',
        'report_type',
        'merged_df',
        'hdr',
        'on_mode_df',
        'limit_funcs',
        'rsdf',
        'area',
        'standby_df',
        'waketimes',
        'test_specs_df',
    ]
    check_report_data(report_data, expected_data)
    make_compliance_report(report_data)
    

if __name__ == '__main__':
    main()