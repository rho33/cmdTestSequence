"""Usage:
report.exe  <data_folder> [options]

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
from pathlib import Path
import numpy as np
import pandas as pd
from reportlab.lib.units import inch
import reportlab_sections as rls
import plots
import report_data as rd

import logfuncs as lf
import filefuncs as ff
from error_handling import skip_and_warn


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

    def round_if_float(x, decimals=1):
        if isinstance(x, float):
            return round(x, decimals)
        else:
            return x
    cdf = cdf.applymap(round_if_float)
    return cdf


def get_title_page(report_title, model):
    if report_title is None:
        report_title = 'TV Power Measurement Report'
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
        canvas.setFont(font, 36)
        title_y = 600
        canvas.drawCentredString(306, title_y, report_title)
        canvas.setFont(font, 22)
        canvas.drawCentredString(306, title_y-50, f'Model: {model}')
        canvas.line(x1=inch, x2=7.5*inch, y1=title_y+37, y2=title_y+37)
        canvas.line(x1=inch, x2=7.5 * inch, y1=title_y - 67, y2=title_y - 67)
        canvas.setFont('Calibri-Bold', 20)
        canvas.drawCentredString(306, neea_logo_y+neea_logo_height+.25*inch, 'Funded By:')
        canvas.drawCentredString(306, pcl_logo_y + pcl_logo_height, 'Prepared By:')
    
        canvas.setFont(font, 16)
        canvas.restoreState()
    
    return title_page
    
    
def on_mode_df_style(on_mode_df, report_type):
    # todo implement estar boolean (report_type
    style = [('BACKGROUND', (0, -1), (-1, -1), 'lightgrey')]
    
    for i, row in on_mode_df.iterrows():
        if pd.notnull(row['ratio']):
            if isinstance(row['ratio'], str):
                if eval(row['ratio']) == 1:
                    color = 'green'
                else:
                    color = 'red'
            else:
                if row['ratio']<1:
                    color = 'green'
                else:
                    color = 'red'
            style.append(('BACKGROUND', (-1, i + 1), (-1, i + 1), color))
    
    # for i, val in enumerate(on_mode_df['ratio']<1):
    #     if val:
    #         color = 'green'
    #         style.append(('BACKGROUND', (-1, i + 1), (-1, i + 1), color))
    #     elif pd.notnull(on_mode_df['limit'].iloc[i]):
    #         color = 'red'
    #         style.append(('BACKGROUND', (-1, i + 1), (-1, i + 1), color))

    style += [
        ('BACKGROUND', (0, 0), (-1, 0), 'lightgrey'),
        ('FONTNAME', (0, 0), (-1, -1), 'Calibri'),
        ('BOX', (0, 0), (-1, -1), 1.0, 'black'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER')
    ]
    break_lines = [i + 1 for i, test_name in on_mode_df['test_name'].iteritems() if 'measured' in test_name]
    for i in break_lines:
        style.append(('BOX', (0, 1), (-1, i), 1.0, 'black'))
    return style


def standby_df_style(standby_df):
    style = []
    for i, val in enumerate(standby_df['watts']<standby_df['limit']):
        if val:
            color = 'green'
            style.append(('BACKGROUND', (-1, i + 1), (-1, i + 1), color))
        elif pd.notnull(standby_df['limit'].iloc[i]):
            color = 'red'
            style.append(('BACKGROUND', (-1, i + 1), (-1, i + 1), color))

    style += [
        ('BACKGROUND', (0, 0), (-1, 0), 'lightgrey'),
        ('FONTNAME', (0, 0), (-1, -1), 'Calibri'),
        ('GRID', (0, 0), (-1, -1), .25, 'black'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER')
    ]
    return style


def get_limit_func_strings(limit_funcs, hdr):
    def get_func_str(limit_func):
        """Crete a string to display the power limit function."""
        coeffs = limit_func.keywords
        func_str = f"{coeffs['sf']:.2f}*(({coeffs['a']:.3f}*area+{coeffs['b']:.2f})*({coeffs['e']:.2f}*luminance+{coeffs['f']:.2f}) + {coeffs['c']:.2f}*area+{coeffs['d']:.2f})"
        if 'power_cap_func' in coeffs.keys():
            pcf = coeffs['power_cap_func'].keywords
            power_cap_func_str = f"{pcf['sf']:.2f}*(({pcf['a']:.3f}*area)+{pcf['b']:.3f})"
            func_str = f'Minimum of:<br/>1. {func_str}<br/>2. {power_cap_func_str}'
        return func_str
    lfs = {
        'default': '<strong>Default PPS Power Limit Function</strong><br/>' + get_func_str(limit_funcs['default']),
        'brightest': '<strong>Brightest PPS Power Limit Function</strong><br/>' + get_func_str(limit_funcs['brightest']),
        'hdr': '<strong>HDR Default PPS Power Limit Function</strong><br/>' + get_func_str(limit_funcs['hdr'])
    }
    return lfs


@skip_and_warn
def add_persistence_summary(report, persistence_dfs):
    with report.new_section('Persistence Summary', page_break=False) as persistence_summary:
        
        with persistence_summary.new_section('SDR Persistence') as sdr_persistence:
            sdr_persistence.create_element('sdr_persistence', persistence_dfs['sdr'], save=False)
        
        hdr10_df = persistence_dfs.get('hdr_10')
        if hdr10_df is not None and not hdr10_df.empty:
            with persistence_summary.new_section('HDR10 Persistence') as hdr_persistence:
                hdr_persistence.create_element('hdr10_persistence', hdr10_df, save=False)
        
        hlg_df = persistence_dfs.get('hlg')
        if hlg_df is not None and not hlg_df.empty:
            with persistence_summary.new_section('HLG Persistence') as hlg_persistence:
                hlg_persistence.create_element('hlg_persistence', hlg_df, save=False)
        
        dv_df = persistence_dfs.get('dolby_vision')
        if dv_df is not None and not dv_df.empty:
            with persistence_summary.new_section('Dolby Vision Persistence') as dv_persistence:
                dv_persistence.create_element('dv_persistence', dv_df, save=False)
                
    return report

@skip_and_warn
def add_compliance_section(report, merged_df, on_mode_df, report_type, limit_funcs, hdr, rsdf, area, standby_df,
                           waketimes, **kwargs):
    
        
    with report.new_section('Compliance with Additional Tests', page_break=False) as cat:
        
        
        with cat.new_section('On Mode Tests') as on_mode_tests:
            @skip_and_warn
            def add_on_mode_tests(report):
                table_df = clean_rsdf(on_mode_df, cols=on_mode_df.columns)
                style = on_mode_df_style(on_mode_df, report_type)
                on_mode_tests.create_element('on mode table', table_df, grid_style=style)
                if report_type == 'estar':
                    # todo: implement estar text
                    #   probably dependent on how get_on_mode_df implements
                    #   potentially include within same function
                    pass
                else:
                    on_mode_tests.create_element('text', 'Average Measured / Limit must be less than 1.0 to comply')
                
                # display power limit functions below on mode table
                limit_func_strings = get_limit_func_strings(limit_funcs, hdr)
                on_mode_tests.create_element('default limit function', limit_func_strings['default'])
                on_mode_tests.create_element('brightest limit function', limit_func_strings['brightest'])
                if hdr:
                    on_mode_tests.create_element('hdr limit function', limit_func_strings['hdr'])
                
                # add scatter plot for each pps showing tv power measurements in relation to the relevant limit function line
                for pps in ['default', 'brightest']:
                    on_mode_tests.create_element(
                        f'{pps} dimming plot',
                        plots.dimming_line_scatter(pps, rsdf, area, limit_funcs)
                    )
                if hdr:
                    on_mode_tests.create_element(
                        'hdr dimming plot',
                        plots.dimming_line_scatter('hdr', rsdf, area, limit_funcs)
                    )
            add_on_mode_tests(report)
        with cat.new_section('Standby') as standby:
            # add standby table
            @skip_and_warn
            def add_standby(report):
                table_df = clean_rsdf(standby_df, standby_df.columns)
                standby.create_element('table', table_df, grid_style=standby_df_style(standby_df))
                
                # show standby wake times below standby table
                standby_tests = [test for test in rsdf.test_name.unique() if 'standby' in test]
                s = '<b>Time to Wake from Standby</b><br />'
                s += '<br />'.join([f"{test}: {waketimes[test]} seconds" for test in standby_tests])
                standby.create_element('waketimes', s)
                
                # time vs power (line) plot showing all standby tests
                standby.create_element('standby_plot', plots.standby(merged_df, standby_tests))
            add_standby(report)
    return report

@skip_and_warn
def add_apl_power(report, test_name, merged_df, rsdf, section_name=None, **kwargs):
    table_df = rsdf.query('test_name==@test_name')
    if not section_name:
        tag = table_df.index[0]
        if tag.is_integer():
            tag = int(tag)
        section_name = f'Test {tag} - {test_name}'

    with report.new_section(section_name) as section:
        table_df = clean_rsdf(table_df)
        section.create_element('table', table_df, save=False)
        section.create_element(f'{section_name}plot', plots.apl_watts_scatter(merged_df, test_name))
    return report

@skip_and_warn
def add_supplemental(report, rsdf, merged_df, hdr, lum_df, spectral_df, report_type, **kwargs):
    with report.new_section('Supplemental Test Results', page_break=False) as supp:
        @skip_and_warn
        def add_stabilization(report):
            with supp.new_section('Stabilization') as stab:
                # table and line plot showing stabilization tests
                stab_tests = [test for test in rsdf.test_name.unique() if 'stabilization' in test]
                table_df = clean_rsdf(rsdf.query('test_name.isin(@stab_tests)'))
                stab.create_element('table', table_df)
                stab.create_element('plot', plots.stabilization(merged_df, stab_tests))
        add_stabilization(report)
        
        with supp.new_section("APL' vs Power Charts", page_break=False)as apl_power:
            # APL vs power scatter plots for each pps (w/ line of best fit)
            apl_power = add_apl_power(apl_power, 'default', merged_df, rsdf, section_name='Default PPS: SDR')
            apl_power = add_apl_power(apl_power, 'brightest', merged_df, rsdf, section_name='Brightest PPS: SDR')
            if hdr:
                apl_power = add_apl_power(apl_power, 'hdr10', merged_df, rsdf, section_name='Default PPS: HDR')
        with supp.new_section('Light Directionality', page_break=False) as ld:
            @skip_and_warn
            def add_light_directinality(report):
                with ld.new_section("Average Luminance Along TV's Horizontal Axis", numbering=False) as x_nits:
                    x_nits.create_element('x nits plot', plots.x_nits(lum_df))
                with ld.new_section("Average Luminance Along TV's Vertical Axis", numbering=False) as y_nits:
                    y_nits.create_element('y nits plot', plots.y_nits(lum_df))
                with ld.new_section('Luminance Heatmap', numbering=False) as heatmap:
                    heatmap.create_element('heatmap', plots.nits_heatmap(lum_df))

            add_light_directinality(report)
        
        # todo: add spectral profile section for PCL tests
        if report_type == 'pcl':
            @skip_and_warn
            def add_spectral_power_distribution(report):
                with supp.new_section('Spectral Power Distribution') as spd:
                    spd.create_element('spectral plot', plots.spectral_power_distribution(spectral_df))
                    spd.create_element('chromaticity plot', plots.chromaticity(spectral_df))
                    # todo chromaticity table
            add_spectral_power_distribution(report)
    return report

@skip_and_warn
def add_test_results_table(report, rsdf, **kwargs):
    # Test Results Table
    with report.new_section('Test Results Table') as table:
        table.create_element('table', clean_rsdf(rsdf))
    return report

@skip_and_warn
def add_test_results_plots(report, rsdf, merged_df, **kwargs):
    '''Test Specifics section displays test metadata and tv specs in table'''
    with report.new_section('Test Result Plots', page_break=False) as trp:
        for test_name in rsdf['test_name']:
            tdf = merged_df.query('test_name==@test_name').reset_index()
            tag = tdf.iloc[0]['tag']
            if tag.is_integer():
                tag = int(tag)
            with trp.new_section(f'Test {tag} - {test_name}', numbering=False) as tn:
                table_df = clean_rsdf(rsdf.query('test_name==@test_name'))
                tn.create_element(f'{test_name} table', table_df, save=False)
                tn.create_element(f'{test_name} plot', plots.standard(tdf))
    return report

@skip_and_warn
def add_test_specs(report, test_specs_df, **kwargs):
    with report.new_section('Test Specifics') as test_specs:
        style = [
            ('BACKGROUND', (0, 0), (0, -1), 'lightgrey'),
            ('FONTNAME', (0, 0), (-1, -1), 'Calibri'),
            ('GRID', (0, 0), (-1, -1), 0.25, 'black'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]
        test_specs.create_element('test spec table', test_specs_df.reset_index(), grid_style=style, header=False)
    return report

def get_content_page(model, test_date):
    def content_page(canvas, doc):
        canvas.saveState()
        canvas.setFont('Calibri', 12)
        canvas.drawRightString(7.5*inch, .8*inch, "Page %d | %s   %s" % (doc.page, model, test_date))
        canvas.restoreState()
    return content_page


def build_report(report,  filename, data_folder, model, test_date, report_title=None, **kwargs):
    content_page = get_content_page(model, test_date)
    title_page = get_title_page(report_title, model)
    path_str = str(Path(data_folder).joinpath(filename))
    doc = rls.make_doc(path_str, font='Calibri', title_page=title_page, content_page=content_page)
    doc.multiBuild(report.story())
    
    
def make_report(report_data):
    """Create the pdf report from the test data."""
    report = ISection(name='report')
    report = add_test_specs(report, **report_data)
    if report_data['report_type'] == 'pcl':
        report = add_persistence_summary(report, **report_data)

    report = add_compliance_section(report, **report_data)
    report = add_supplemental(report, **report_data)
    report = add_test_results_table(report, **report_data)
    report = add_test_results_plots(report, **report_data)
    
    filename = {'estar': 'ENERGYSTAR-report.pdf',
                   'alternative-report.pdf': 'alternative',
                   'pcl': 'pcl-report.pdf'}.get(report_data['report_type'])
    build_report(report, filename, report_data['data_folder'], report_data['model'], report_data['test_date'])


def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'report.log')
    paths = ff.get_paths(data_folder)
    
    if Path(sys.path[0]).joinpath('simple.txt').exists():
        merged_df = rd.get_merged_df(paths, data_folder)
        rd.get_results_summary_df(merged_df, data_folder, waketimes={})
        rd.get_ccf_df(merged_df, data_folder)
    else:
        report_data = rd.get_report_data(paths, data_folder, docopt_args)
        ISection.save_content_dir = Path(data_folder).joinpath('Elements')
        make_report(report_data)


if __name__ == '__main__':
    main()
