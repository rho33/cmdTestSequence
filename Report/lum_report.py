"""Usage:
lum_report.exe  <data_folder> [options]
lum_report.exe file <lum_profile> [options]

Arguments:
  data_folder       folder with test data, also destination folder
  lum_profile       file with luminance profile data

Options:
  -h --help
"""
import sys
sys.path.append('..')
from pathlib import Path
from report_data import get_report_data, check_report_data
from report import add_light_directionality, ISection, build_report, add_test_specs
import logfuncs as lf
import filefuncs as ff


def make_lum_report(report_data):
    report = ISection(name='report')
    # add test specifications to report if available
    if report_data['test_specs_df'] is not None:
        report = add_test_specs(report, **report_data)
    with report.new_section('Light Directionality', page_break=False) as ld:
        ld = add_light_directionality(ld, numbering=False, **report_data)
    report_name = f'lum-report.pdf'
    build_report(report, report_name, **report_data)


def main():

    logger, docopt_args, data_folder = lf.start_script(__doc__, 'lum_report.log')

    if data_folder is None:
        paths = {'lum_profile': Path(docopt_args['<lum_profile>'])}
        
    else:
        paths = ff.get_paths(data_folder)

    report_data = get_report_data(paths, data_folder, docopt_args)
    report_data['data_folder'] = paths['lum_profile'].parent
    expected_data = [
        'lum_df',
        'test_specs_df'
    ]
    check_report_data(report_data, expected_data)
    make_lum_report(report_data)


if __name__ == '__main__':
    main()