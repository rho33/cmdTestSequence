"""Usage:
report.exe  <data_folder>

Arguments:
  data_folder       folder with test data, also destination folder

Options:
  -h --help
"""
import sys
from pathlib import Path
from functools import partial
import numpy as np
import pandas as pd
from docopt import docopt
from reportlab.lib.units import inch
import reportlab_sections as rls
import plots
import merge


class ISection(rls.Section):
    intro_text = pd.read_csv(Path(sys.path[0]).joinpath('intro-text.csv'), index_col='section_path')['text'].replace(
        {np.nan: None}).to_dict()
    # intro_text = pd.read_csv('intro-text.csv', index_col='section_title')['text'].replace({np.nan: None}).to_dict()

    def insert_intro_text(self):
        text = self.intro_text.get(self.path_str)
        if text:
            self.create_element('intro_text', text)

    def new_section(self, title, numbering=True, **kw):
        """Create and Return new child Section (subsection)."""
        new_section = type(self)(name=title, elements={}, parent=self, **kw)
        new_section.elements['title'] = rls.Element.from_content(title, heading=True, numbering=numbering, level=self.depth + 1)
        new_section.insert_intro_text()
        return new_section


def get_results_summary_df(merged_df, waketimes):
    """Create a dataframe with one line per test showing test info and test results (average watts and nits)."""
    rsdf = merged_df.groupby(['tag']).first()
    cols = ['test_name', 'test_time', 'preset_picture', 'video', 'mdd', 'abc', 'lux', 'qs']
    cols = [col for col in cols if col in rsdf.columns]
    rsdf = rsdf[cols]
    avg_cols = ['watts', 'nits', "APL'"]
    rsdf = pd.concat([rsdf, merged_df.groupby(['tag']).mean()[avg_cols]], axis=1)
    rsdf['waketime'] = rsdf['test_name'].apply(waketimes.get)

    for i, row in rsdf.reset_index().iterrows():
        if 'standby' in row['test_name']:
            last20_df = merged_df[merged_df['tag'] == row['tag']].iloc[-20 * 60]
            for col in ['watts', 'nits']:
                rsdf.loc[row['tag'], col] = last20_df[col].mean()

    return rsdf


def clean_rsdf(rsdf, cols=None):
    """Clean the results summary dataframe so that it can be displayed in a pdf table."""
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
        'tag': 'Test',
        'test_name': 'Test Name',
        'test_time': 'Test Time (s)',
        'video': 'Video',
        "APL'": "Avg APL' (%)",

        'abc': 'ABC',
        'lux': 'Lux',
        'preset_picture': 'Preset Picture',
        'mdd': 'MDD',
        'qs': 'QS',

        'waketime': 'Wake Time (s)',
        'nits': 'Avg Luminance (Nits)',
        'limit': 'Power Limit (W)',
        'watts': 'Avg Power (W)',
        'ratio': 'Power/Power Limit',
    }
    if cols is None:
        cols = [col for col in rename_cols.keys() if col in rsdf.columns]
    cdf = rsdf[cols].copy()
    if 'test_time' in cdf.columns:
        cdf['test_time'] = cdf['test_time'].astype(int)
    if 'video' in cdf.columns:
        cdf['video'] = cdf['video'].apply(lambda x: rename_video.get(x, x))

    cdf = cdf.dropna(axis=1, how='all')
    cdf = cdf.rename(columns=rename_cols)
    cdf = cdf.round(decimals=1)
    return cdf


def get_waketimes(test_seq_df, data_df):
    """Calculate wake times from the test data and return as a dictionary."""
    waketimes = {}
    for _, row in test_seq_df.iterrows():
        if 'waketime' in row['test_name']:
            standby_tag = row['tag'] - 1
            standby_test = test_seq_df.query('tag==@standby_tag')['test_name'].iloc[0]
            wt_tag = row['tag'] + .1
            waketime = len(data_df.query('Tag==@wt_tag'))
            waketimes[standby_test] = waketime
    return waketimes


def get_test_specs_df(merged_df, data_folder):
    """Create a dataframe from test-metadata.csv and test data which displays the test specifics."""
    test_specs_df = pd.read_csv(Path(data_folder).joinpath('test-metadata.csv'), header=None, index_col=0)
    test_specs_df.columns = [0]

    start_date = pd.to_datetime(merged_df['time']).min().date()
    start_time = pd.to_datetime(merged_df['time']).min().time()
    end_time = pd.to_datetime(merged_df['time']).max().time()
    duration = pd.to_datetime(merged_df['time']).max() - pd.to_datetime(merged_df['time']).min()
    data = {
        'Test Start Date': start_date,
        'Test Start Time': start_time,
        'Test End Time': end_time,
        'Test Duration': duration
    }

    beginning_rows = pd.DataFrame.from_dict(data, orient='index')
    test_specs_df = pd.concat([beginning_rows, test_specs_df])

    return test_specs_df


def get_on_mode_df(rsdf, limit_funcs, area):
    """Create a dataframe and corresponding reportlab TableStyle data which displays the results of on mode testing."""
    def add_pps_tests(on_mode_df, cdf, abc_off_test, abc_on_tests, limit_func):
        on_mode_df = on_mode_df.append(cdf.loc[abc_off_test])

        abc_off_pwr = on_mode_df.loc[abc_off_test, 'watts']
        abc_off_lum = on_mode_df.loc[abc_off_test, 'nits']
        if abc_on_tests:
            for test in abc_on_tests:
                on_mode_df = on_mode_df.append(cdf.loc[test])
            abc_on_pwr = on_mode_df.loc[abc_on_tests, 'watts'].mean()
            abc_on_lum = on_mode_df.loc[abc_on_tests, 'nits'].mean()
            measured = {
                'nits': np.mean([abc_on_lum, abc_off_lum]),
                'watts': np.mean([abc_on_pwr, abc_off_pwr])
            }
        else:
            measured = {
                'nits': np.mean(abc_off_lum),
                'watts': np.mean(abc_off_pwr)
            }
        measured_name = f'{abc_off_test}_measured'
        on_mode_df = on_mode_df.append(pd.Series(data=measured, name=measured_name))
        limit = limit_func(area=area, luminance=on_mode_df.loc[measured_name, 'nits'])
        on_mode_df.loc[measured_name, 'limit'] = limit
        return on_mode_df

    cdf = rsdf.set_index('test_name')
    on_mode_df = cdf.drop(cdf.index)

    def_abc_tests = [test for test in ['default_100', 'default_35', 'default_12', 'default_3'] if test in cdf.index]
    on_mode_df = add_pps_tests(on_mode_df, cdf, 'default', def_abc_tests, limit_funcs['default'])

    br_abc_tests = [test for test in ['brightest_100', 'brightest_35', 'brightest_12', 'brightest_3'] if
                    test in cdf.index]
    on_mode_df = add_pps_tests(on_mode_df, cdf, 'brightest', br_abc_tests, limit_funcs['brightest'])

    if 'hdr' in cdf.index:
        hdr_abc_tests = [test for test in ['hdr_100', 'hdr_35', 'hdr_12', 'hdr_3'] if test in cdf.index]
        on_mode_df = add_pps_tests(on_mode_df, cdf, 'hdr', hdr_abc_tests, limit_funcs['hdr'])

    on_mode_df = on_mode_df.reset_index()
    on_mode_df['ratio'] = on_mode_df['watts']/on_mode_df['limit']
    data = {'test_name': 'average_measured', 'ratio': on_mode_df['ratio'].mean()}
    on_mode_df = on_mode_df.append(data, ignore_index=True)
    cols = ['test_name', 'preset_picture', 'abc', 'lux', 'mdd', 'nits', 'limit', 'watts', 'ratio']
    cols = [col for col in cols if col in on_mode_df.columns]
    on_mode_df = on_mode_df[cols]




    style = [('BACKGROUND', (0, -1), (-1, -1), 'lightgrey')]
    for i, val in enumerate(on_mode_df['ratio']<1):
        if val:
            color = 'green'
            style.append(('BACKGROUND', (-1, i + 1), (-1, i + 1), color))
        elif pd.notnull(on_mode_df['limit'].iloc[i]):
            color = 'red'
            style.append(('BACKGROUND', (-1, i + 1), (-1, i + 1), color))

    style += [
        #     ('BACKGROUND', (-1, 1), (-1, 1), 'red'),
        ('BACKGROUND', (0, 0), (-1, 0), 'lightgrey'),
        ('FONTNAME', (0, 0), (-1, -1), 'Calibri'),
        ('BOX', (0, 0), (-1, -1), 1.0, 'black'),
        #     ('BOX', (0, 1), (-1, 6), 1.0, 'black'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER')
    ]
    break_lines = [i + 1 for i, test_name in on_mode_df['test_name'].iteritems() if 'measured' in test_name]
    for i in break_lines:
        style.append(('BOX', (0, 1), (-1, i), 1.0, 'black'))
    return on_mode_df, style


def get_standby_df(rsdf):
    """Create a dataframe and corresponding reportlab TableStyle data which displays the results of standby testing."""
    standby_df = rsdf[rsdf['test_name'].apply(lambda x: 'standby' in x)].copy()
    standby_df['limit'] = 2
    cols = ['test_name', 'qs', 'waketime', 'limit', 'watts']
    cols = [col for col in cols if col in standby_df.columns]
    standby_df = standby_df.reset_index()[cols]

    style = []
    for i, val in enumerate(standby_df['watts']<standby_df['limit']):
        if val:
            color = 'green'
            style.append(('BACKGROUND', (-1, i + 1), (-1, i + 1), color))
        elif pd.notnull(standby_df['limit'].iloc[i]):
            color = 'red'
            style.append(('BACKGROUND', (-1, i + 1), (-1, i + 1), color))

    style += [
        #     ('BACKGROUND', (-1, 1), (-1, 1), 'red'),
        ('BACKGROUND', (0, 0), (-1, 0), 'lightgrey'),
        ('FONTNAME', (0, 0), (-1, -1), 'Calibri'),
        ('GRID', (0, 0), (-1, -1), .25, 'black'),
        #     ('BOX', (0, 1), (-1, 6), 1.0, 'black'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER')
    ]

    return standby_df, style


def title_page(canvas, doc):
    """Create a custom title page for the reportlab pdf doc."""
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


def make_report(merged_df, rsdf, light_df, data_folder, waketimes, limit_funcs):
    """Create the pdf report from the test data."""
    report = ISection(name='report')
    # Test Specifics section displays test metadata and tv specs in table
    with report.new_section('Test Specifics') as test_specs:
        test_specs_df = get_test_specs_df(merged_df, data_folder)

        # save a couple variables from test specs for later use in other sections
        area = float(test_specs_df.loc['Screen Area (sq in)', 0])
        test_date = pd.to_datetime(test_specs_df.loc['Test Start Date', 0]).date().strftime('%d-%b-%Y')
        model = f"{test_specs_df.loc['Make', 0].upper()} {test_specs_df.loc['Model', 0].upper()}"

        style = [
            ('BACKGROUND', (0, 0), (0, -1), 'lightgrey'),
            ('FONTNAME', (0, 0), (-1, -1), 'Calibri'),
            ('GRID', (0, 0), (-1, -1), 0.25, 'black'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]
        test_specs.create_element('test spec table', test_specs_df.reset_index(), grid_style=style, header=False)

    with report.new_section('Persistence Summary', page_break=False) as persistence_summary:
        with persistence_summary.new_section('SDR Persistence') as sdr_persistence:
            pass
        hdr = 'hdr' in merged_df.test_name.unique()
        if hdr:
            with persistence_summary.new_section('HDR10 Persistence') as hdr_persistence:
                pass

    with report.new_section('DOE Test Results Summary') as doe:
        pass

    with report.new_section('Compliance with Additional Tests', page_break=False) as cat:
        with cat.new_section('On Mode Tests') as on_mode_tests:
            # add on mode table
            on_mode_df, style = get_on_mode_df(rsdf, limit_funcs, area)
            table_df = clean_rsdf(on_mode_df, cols=on_mode_df.columns)
            on_mode_tests.create_element('on mode table', table_df, grid_style=style)
            on_mode_tests.create_element('text', 'Average Measured / Limit must be less than 1.0 to comply')

            # display power limit functions below on mode table
            def get_func_str(limit_func):
                """Crete a string to display the power limit function."""
                coeffs = limit_func.keywords
                func_str = f"{coeffs['sf']:.2f}*(({coeffs['a']:.3f}*area+{coeffs['b']:.2f})*({coeffs['e']:.2f}*luminance+{coeffs['f']:.2f}) + {coeffs['c']:.2f}*area+{coeffs['d']:.2f})"
                return func_str
            s = '<strong>Default PPS Power Limit Function</strong><br/>' + get_func_str(limit_funcs['default'])
            on_mode_tests.create_element('default limit function', s)
            s = '<strong>Brightest PPS Power Limit Function</strong><br/>' + get_func_str(limit_funcs['brightest'])
            on_mode_tests.create_element('brightest limit function', s)
            if hdr:
                s = '<strong>HDR Default PPS Power Limit Function</strong><br/>' + get_func_str(limit_funcs['hdr'])
                on_mode_tests.create_element('hdr limit function', s)

            # add scatter plot for each pps showing tv power measurements in relation to the relevant limit function line
            for pps in ['default', 'brightest']:
                on_mode_tests.create_element(f'{pps} dimming plot', plots.dimming_line_scatter(pps, rsdf, area, limit_funcs))
            if hdr:
                on_mode_tests.create_element('hdr dimming plot', plots.dimming_line_scatter('hdr', rsdf, area, limit_funcs))

        with cat.new_section('Standby') as standby:
            # add standby table
            standby_tests = [test for test in rsdf.test_name.unique() if 'standby' in test]
            standby_df, style = get_standby_df(rsdf)
            table_df = clean_rsdf(standby_df, standby_df.columns)
            standby.create_element('table', table_df, grid_style=style)

            # show standby wake times below standby table
            s = '<b>Time to Wake from Standby</b><br />'
            s += '<br />'.join([f'{test}: {waketimes[test]} seconds' for test in standby_tests])
            standby.create_element('waketimes', s)

            # time vs power (line) plot showing all standby tests
            standby.create_element('time_plot', plots.standby(merged_df, standby_tests))

    with report.new_section('Supplemental Test Results', page_break=False) as supp:
        with supp.new_section('Stabilization') as stab:
            # table and line plot showing stabilization tests
            stab_tests = [test for test in rsdf.test_name.unique() if 'stabilization' in test]
            table_df = clean_rsdf(rsdf[rsdf['test_name'].isin(stab_tests)])
            stab.create_element('table', table_df)
            stab.create_element('plot', plots.stabilization(merged_df, stab_tests))

        with supp.new_section("APL' vs Power Charts", page_break=False)as apl_power:
            # APL vs power scatter plots for each pps (w/ line of best fit)
            with apl_power.new_section('Default PPS: SDR') as default:
                table_df = clean_rsdf(rsdf[rsdf['test_name']=='default'])
                default.create_element('table', table_df)
                default.create_element('plot', plots.apl_watts_scatter(merged_df, 'default'))
            with apl_power.new_section('Brightest PPS: SDR') as brightest:
                table_df = clean_rsdf(rsdf[rsdf['test_name']=='brightest'])
                brightest.create_element('table', table_df)
                brightest.create_element('plot', plots.apl_watts_scatter(merged_df, 'brightest'))

            if hdr:
                with apl_power.new_section('Default PPS: HDR') as brightest:
                    table_df = clean_rsdf(rsdf[rsdf['test_name'] == 'hdr'])
                    brightest.create_element('table', table_df)
                    brightest.create_element('plot', plots.apl_watts_scatter(merged_df, 'hdr'))

        with supp.new_section('Light Directionality', page_break=False) as ld:
            with ld.new_section("Average Luminance Along TV's Horizontal Axis", numbering=False) as x_nits:
                x_nits.create_element('x nits plot', plots.x_nits(light_df))
            with ld.new_section("Average Luminance Along TV's Vertical Axis", numbering=False) as y_nits:
                y_nits.create_element('y nits plot', plots.y_nits(light_df))
            with ld.new_section('Luminance Heatmap', numbering=False) as heatmap:
                heatmap.create_element('heatmap', plots.nits_heatmap(light_df))


    # Test Results Table
    with report.new_section('Test Results Table') as table:
        table.create_element('table', clean_rsdf(rsdf))
    # All Plots
    with report.new_section('Test Result Plots', page_break=False) as trp:
        for test_name in rsdf['test_name']:
            tdf = merged_df[merged_df['test_name'] == test_name].reset_index()
            tag = tdf.iloc[0]['tag']
            if tag.is_integer():
                tag = int(tag)
            with trp.new_section(f'Test {tag} - {test_name}', numbering=False) as tn:
                table_df = clean_rsdf(rsdf[rsdf['test_name']==test_name])
                tn.create_element(f'{test_name} table', table_df)
                tn.create_element(f'{test_name} plot', plots.standard(tdf))

    # build the pdf document
    path_str = str(Path(data_folder).joinpath('report.pdf'))

    def content_page(canvas, doc):
        canvas.saveState()
        canvas.setFont('Calibri', 12)
        canvas.drawRightString(7.5 * inch, .8 * inch, "Page %d | %s   %s" % (doc.page, model, test_date))
        canvas.restoreState()
    doc = rls.make_doc(path_str, font='Calibri', title_page=title_page, content_page=content_page)
    doc.multiBuild(report.story())


def get_input_from_folder(data_folder):
    """Given the directory, find the correct files based on keywords within the file names and return as a dictionary."""
    paths = {}
    data_folder = Path(data_folder)
    paths['test_seq'] = next(data_folder.glob('*test-sequence*.csv'))
    paths['test_data'] = next(data_folder.glob('*datalog*.csv'))
    paths['lum_profile'] = next(data_folder.glob('*lum profile*.csv'))
    return paths


def main():
    docopt_args = docopt(__doc__)
    data_folder = docopt_args['<data_folder>']
    paths = get_input_from_folder(data_folder)

    test_seq_df = pd.read_csv(paths['test_seq'])
    data_df = pd.read_csv(paths['test_data'], parse_dates=['Timestamp'])
    merged_df = merge.merge_test_data(test_seq_df, data_df)
    merged_df.to_csv(Path(data_folder).joinpath('merged.csv'), index=False)

    waketimes = get_waketimes(test_seq_df, data_df)
    rsdf = get_results_summary_df(merged_df, waketimes)
    rsdf.to_csv(Path(data_folder).joinpath('results-summary.csv'))

    light_df = pd.read_csv(paths['lum_profile'], header=None)

    def power_limit(area, luminance, sf, a, b, c, d, e, f, power_cap=None):
        limit = sf * ((a * area + b) * (e * luminance + f) + c * area + d)
        if power_cap is not None:
            return min(limit, power_cap)
        else:
            return limit
        
    coeffs = pd.read_csv(Path(sys.path[0]).joinpath('coeffs.csv'), index_col='coef').to_dict()
    # todo: change power cap with cli option (probably an estar vs va option)
    power_cap = True
    if not power_cap:
        del coeffs['power_cap']
    
    limit_funcs = {func_name: partial(power_limit, **coeff_vals) for func_name, coeff_vals in coeffs.items()}

    make_report(merged_df, rsdf, light_df, data_folder, waketimes, limit_funcs)


if __name__ == '__main__':
    main()
