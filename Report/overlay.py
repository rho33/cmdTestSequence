"""Usage:
overlay.exe  <data_folder> <test_name1> <test_name2> [options]

Arguments:
  data_folder       folder with test data, also destination folder
  tag1              first test tag to be charted
  tag2              second test tag to be charted

Options:
  -h --help
"""
import sys
sys.path.append('..')
from report_data import get_report_data, check_report_data
from report import add_overlay, ISection, build_report, add_test_specs
import logfuncs as lf
import filefuncs as ff


def make_overlay_report(report_data, test_names):
    report = ISection(name='report')
    # add test specifications to report if available
    if report_data['test_specs_df'] is not None:
        report = add_test_specs(report, **report_data)
    with report.new_section('Overlay Chart') as oc:
        oc = add_overlay(oc, test_names=test_names, **report_data)
    report_name = f'overlay-{test_names[0]}-{test_names[1]}.pdf'
    build_report(report, report_name, **report_data)


def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'lum_report.log')
    test_names = [docopt_args['<test_name1>'], docopt_args['<test_name2>']]
    paths = ff.get_paths(data_folder)
    report_data = get_report_data(paths, data_folder, docopt_args)
    expected_data = [
        'rsdf',
        'merged_df'
        'test_specs_df'
    ]
    check_report_data(report_data, expected_data)
    make_overlay_report(report_data, test_names)
    
    
if __name__ == '__main__':
    main()