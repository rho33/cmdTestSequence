"""Usage:
report.exe  <data_folder>

Arguments:
  data_folder       folder with test data, also destination folder

Options:
  -h --help
"""
from pathlib import Path
import pandas as pd
from docopt import docopt
from merge import merge_test_data
from reportlab.lib.units import inch
import reportlab_sections as rls
import plots


def get_input_from_folder(data_folder):
    paths = {}
    data_folder = Path(data_folder)
    paths['test_seq'] = next(data_folder.glob('*test-sequence*.csv'))
    paths['test_data'] = next(data_folder.glob('*second*.csv'))
    return paths


def get_results_summary_df(merged_df):
    rsdf = merged_df.groupby(['tag']).first()
    cols = ['test_name', 'test_time', 'preset_picture', 'video', 'mdd', 'abc', 'lux', 'qs']
    cols = [col for col in cols if col in rsdf.columns]
    rsdf = rsdf[cols]
    avg_cols = ['watts', 'nits', "APL'"]
    rsdf = pd.concat([rsdf, merged_df.groupby(['tag']).mean()[avg_cols]], axis=1)

    for i, row in rsdf.reset_index().iterrows():
        if 'standby' in row['test_name']:
            last20_df = merged_df[merged_df['tag'] == row['tag']].iloc[-20 * 60]
            for col in ['watts', 'nits']:
                rsdf.loc[row['tag'], col] = last20_df[col].mean()

    return rsdf


def clean_rsdf(rsdf):
    rename_video = {
        'dg': 'Dark Grey Pattern',
        'dg_sdr': 'Dark Grey Pattern',
        'dg_hdr': 'Dark Grey Pattern',
        '2%': 'SDR 2% Peak Brightness',
        '2%_sdr': 'SDR 2% Peak Brightness',
        '2%_hdr': 'HDR 2% Peak Brightness',
        '10%': 'SDR 10% Peak Brightness',
        '10%_sdr': 'SDR 10% Peak Brightness',
        '10%_hdr': 'HDR 10% Peak Brightness',
        '3bar': '3-Bar',
        '3bar_100nit': '3-bar',
        '3bar_sdr': '3-Bar',
        'color': 'RGB Color Pattern',
        'color_sdr': 'RGB Color Pattern',
        'color_hdr': 'HDR RGB Color Pattern',
        'sdr': 'IEC SDR',
        'nrdc_sdr': 'NRDC SDR',
        'clasp_dv': 'CLASP Dolby Vision',
        'clasp_hlg': 'CLASP HLG',
        'clasp_hdr10': 'CLASP HDR10',
        'clasp_hdr': 'CLASP HDR10',
        'standby': 'STANDBY TEST'
}
    rename_cols = {
        'test_name': 'Test Name',
        'test_time': 'Test Time (s)',
        'preset_picture': 'Preset Picture',
        'video': 'Video',
        'mdd': 'MDD',
        'qs': 'QS',
        'watts': 'Avg Power (W)',
        'nits': 'Avg Luminance (Nits)',
        "APL'": "Avg APL' (%)",
        'abc': 'ABC',
        'lux': 'Lux',
        'tag': 'Test'
    }

    cdf = rsdf.copy()
    cdf['test_time'] = cdf['test_time'].astype(int)
    cdf['video'] = cdf['video'].apply(lambda x: rename_video.get(x, x))
    cdf = cdf.rename(columns=rename_cols)
    cdf = cdf.round(decimals=1)
    return cdf


def get_waketimes(test_seq_df, data_df):
    waketimes = {}
    for _, row in test_seq_df.iterrows():
        if 'waketime' in row['test_name']:
            standby_tag = row['tag'] - 1
            standby_test = test_seq_df.query('tag==@standby_tag')['test_name'].iloc[0]
            wt_tag = row['tag'] + .1
            waketime = len(data_df.query('Tag==@wt_tag'))
            waketimes[standby_test] = waketime
    return waketimes


def title_page(canvas, doc):
    canvas.saveState()

    pcl_logo_width, pcl_logo_height = 1.33*inch*1.35, 1.43*inch*1.35
    pcl_logo_x = 306 - pcl_logo_width/2
    pcl_logo_y = 2*inch
    pcl_logo_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\Report\images\pcl-logo.jpg'
    canvas.drawImage(pcl_logo_path, pcl_logo_x, pcl_logo_y, width=pcl_logo_width, height=pcl_logo_height,
                     preserveAspectRatio=True)

    neea_logo_width, neea_logo_height = 1.24*inch, .82*inch
    neea_logo_y = 5*inch
    neea_logo_x = 306 - neea_logo_width/2
    neea_logo_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\Report\images\neea.png'
    canvas.drawImage(neea_logo_path, neea_logo_x, neea_logo_y, width=neea_logo_width, height=neea_logo_height,
                     preserveAspectRatio=True)
    font='Calibri'
    model='Demo Model'
    canvas.setFont(font, 36)
    title_y = 600
    canvas.drawCentredString(306, title_y, 'TV Power Measurement Report')
    canvas.setFont(font, 22)
    canvas.drawCentredString(306, title_y-50, 'Model: {}'.format(model))
    canvas.line(x1=inch, x2=7.5*inch, y1=title_y+37, y2=title_y+37)
    canvas.line(x1=inch, x2=7.5 * inch, y1=title_y - 67, y2=title_y - 67)
    canvas.setFont('Calibri-Bold', 20)
    canvas.drawCentredString(306, neea_logo_y+neea_logo_height+.25*inch, 'Funded By:')
    canvas.drawCentredString(306, pcl_logo_y + pcl_logo_height, 'Prepared By:')

    canvas.setFont(font, 16)
#     canvas.drawCentredString(306, inch, title_test_date)
    canvas.restoreState()


def make_report(merged_df, rsdf, data_folder, waketimes):
    report = rls.Section(name='')

    with report.new_section('Test Specifics') as test_specs:
        pass

    with report.new_section('Persistence Summary', page_break=False) as persistence_summary:
        with persistence_summary.new_section('SDR Persistence') as sdr_persistence:
            pass
        hdr = True # todo: hdr logic
        if hdr:
            with persistence_summary.new_section('HDR10 Persistence') as hdr_persistence:
                pass

    with report.new_section('DOE Test Results Summary') as doe:
        pass

    with report.new_section('Compliance with Additional Tests', page_break=False) as cat:
        with cat.new_section('Summary') as summary:
            pass
        with cat.new_section('On Mode Tests', page_break=False) as on_mode_tests:
            with on_mode_tests.new_section('Summary') as summary:
                pass
            with on_mode_tests.new_section('Table and Chart', page_break=False) as table_chart:
                pass
        with cat.new_section('Standby') as standby:
            standby_tests = [test for test in rsdf.test_name.unique() if 'standby' in test]
            standby.create_element('table', rsdf[rsdf['test_name'].isin(standby_tests)])
            s = '<b>Time to Wake from Standby</b><br />'
            s += '<br />'.join([f'{test}: {waketimes[test]} seconds' for test in standby_tests])
            standby.create_element('waketimes', s)
            standby.create_element('time_plot', plots.standby(merged_df, standby_tests))
            stby_df = rsdf.query('test_name.isin(@standby_tests)')
            standby.create_element('bar_plot', plots.standby_bar(stby_df))



    with report.new_section('Supplemental Test Results', page_break=False) as supp:
        with supp.new_section('Additional Test Data', page_break=False) as atd:
            with atd.new_section('Stabilization') as stab:
                stab_tests = [test for test in rsdf.test_name.unique() if 'stabilization' in test]
                stab.create_element('table', rsdf[rsdf['test_name'].isin(stab_tests)])
                stab.create_element('plot', plots.stabilization(merged_df, stab_tests))

            with atd.new_section("APL' vs Power Charts", page_break=False)as apl_power:

                with apl_power.new_section('Default PPS: SDR') as default:
                    default.create_element('table', rsdf[rsdf['test_name']=='default'])
                    default.create_element('plot', plots.apl_watts_scatter(merged_df, 'default'))
                with apl_power.new_section('Brightest PPS: SDR') as brightest:
                    brightest.create_element('table', rsdf[rsdf['test_name']=='brightest'])
                    brightest.create_element('plot', plots.apl_watts_scatter(merged_df, 'brightest'))
                hdr = True # todo: hdr logic
                if hdr:
                    with apl_power.new_section('Default PPS: HDR') as brightest:
                        brightest.create_element('table', rsdf[rsdf['test_name'] == 'hdr'])
                        brightest.create_element('plot', plots.apl_watts_scatter(merged_df, 'hdr'))
    # Test Results Table
    with report.new_section('Test Results Table') as table:
        table.create_element('table', clean_rsdf(rsdf))
    # All Plots
    with report.new_section('Test Result Plots', page_break=False) as trp:
        for test_name in rsdf['test_name']:
            tdf = merged_df[merged_df['test_name'] == test_name]
            tag = tdf.iloc[0]['tag']
            if tag.is_integer():
                tag = int(tag)
            with trp.new_section(f'Test {tag} - {test_name}', numbering=False) as tn:
                tn.create_element(test_name, plots.standard(tdf))

    path_str = str(Path(data_folder).joinpath('report.pdf'))
    doc = rls.make_doc(path_str, font='Calibri', title_page=title_page)
    doc.multiBuild(report.story())


def main():
    docopt_args = docopt(__doc__)
    data_folder = docopt_args['<data_folder>']
    paths = get_input_from_folder(data_folder)

    test_seq_df = pd.read_csv(paths['test_seq'])
    data_df = pd.read_csv(paths['test_data'], parse_dates=['Timestamp'])
    merged_df = merge_test_data(test_seq_df, data_df)
    merged_df.to_csv(Path(data_folder).joinpath('merged.csv'), index=False)

    rsdf = get_results_summary_df(merged_df)
    rsdf.to_csv(Path(data_folder).joinpath('results-summary.csv'))

    waketimes = get_waketimes(test_seq_df, data_df)
    make_report(merged_df, rsdf, data_folder, waketimes)


if __name__ == '__main__':
    main()
