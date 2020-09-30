"""Usage:
compliance_report.exe  <data_folder> [options]

Arguments:
  data_folder       folder with test data, also destination folder

Options:
  -h --help
  -e
  -v
  -p
"""
import sys
sys.path.append('..')
import warnings
from report_data import get_report_data
from report import add_compliance_section, ISection, build_report, add_test_specs
import logfuncs as lf
import filefuncs as ff

# def get_compliance_report_data(paths, data_folder, docopt_args):
#
#     data = {}
#     data['data_folder'] = data_folder
#     data['report_type'] = rd.get_report_type(docopt_args, data_folder)
#     data['merged_df'] = rd.get_merged_df(paths, data_folder)
#     data['waketimes'] = rd.get_waketimes(paths)
#     data['rsdf'] = rd.get_results_summary_df(data['merged_df'], data_folder, data['waketimes'])
#     data['test_date'] = pd.to_datetime(data['test_specs_df'].loc['Test Start Date', 0]).date().strftime('%d-%b-%Y')
#     data['area'] = float(data['test_specs_df'].loc['Screen Area (sq in)', 0])
#     data['on_mode_df'] = get_on_mode_df(data['rsdf'], data['limit_funcs'], data['area'], data['report_type'])
#     on_mode_df = rd.get_on_mode_df(data['rsdf'], data['limit_funcs'], data['area'], data['report_type'])
#     # todo: force report type
#     limit_funcs = rd.get_limit_funcs(report_type)
#     hdr = 'hdr' in merged_df.test_name.unique()
#
#     area = float(data['test_specs_df'].loc['Screen Area (sq in)', 0])
#     standby_df = get_standby_df(rsdf)


def make_compliance_report(report_data):
    report = ISection(name='report')
    report = add_test_specs(report, **report_data)
    report = add_compliance_section(report, **report_data)
    report_name = f'compliance-report.pdf'
    build_report(report, report_name, **report_data)
    

def check_data(report_data, expected_data):
    warnings.filterwarnings('always', category=UserWarning)
    for item in expected_data:
        if item not in report_data.keys():
            msg = f'\nMissing Data Item: {item}\nReport may not be complete.'
            warnings.warn(msg)
            
            
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
    check_data(report_data, expected_data)
    make_compliance_report(report_data)
    

if __name__ == '__main__':
    main()