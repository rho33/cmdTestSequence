"""Usage:
apl_power_charts.exe  <data_folder> [options]

Arguments:
  data_folder       folder with test data, also destination folder

Options:
  -h --help
"""
from pathlib import Path
from core.report.report_data import get_report_data, check_report_data
from report import ISection, build_report, add_test_specs, clean_rsdf, add_apl_power

import core.logfuncs as lf
import core.filefuncs as ff


def make_report(report_data):
    report = ISection(name='report')
    report = add_test_specs(report, **report_data)
    merged_df = report_data['merged_df']
    with report.new_section("APL' vs Power Charts", page_break=False) as apl_power:
        for test_name in merged_df['test_name'].unique():
            if 'standby' not in test_name:
                apl_power = add_apl_power(apl_power, test_name, **report_data)
    filename = f'apl-power-charts.pdf'
    report_title = "APL' vs Power Charts All Tests"
    build_report(report, filename, report_title=report_title, **report_data)
    
    
def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'apl_power_report.log')
    paths = ff.get_paths(data_folder)
    report_data = get_report_data(paths, data_folder, docopt_args)
    ISection.save_content_dir = Path(data_folder).joinpath('APLvsPowerCharts')
    expected_data = [
        'data_folder',
        'merged_df',
        'rsdf',
        'test_specs_df'
    ]
    check_report_data(report_data, expected_data)
    make_report(report_data)


if __name__ == '__main__':
    main()