"""Usage:
report.exe  <data_folder> [options]

Arguments:
  data_folder       folder with test data, also destination folder

Options:
  -h --help
  -e            force ENERGYSTAR report type
  -v            force VA report type
  -p            force PCL report type
  --omit        omit ENERGYSTAR compliance section
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak
import core.report.reportlab_sections as rls
import core.report.plots as plots
import core.report.report_data as rd

import core.logfuncs as lf
import core.filefuncs as ff
from core.error_handling import skip_and_warn


class ISection(rls.Section):
    """rls.Sections subclass to allow adding introductory text (text at beginning of a section) from external file"""
    
    # read intro text csv into dictionary and save as class variable
    # intro_text keys (first column of csv) should be node path ("/" separators) to desired report section
    intro_text = pd.read_csv(Path(sys.path[0]).joinpath(r'config\intro-text.csv'), index_col='section_path')['text'].replace(
        {np.nan: None}).to_dict()

    def insert_intro_text(self):
        """Check if intro text exists for current section and insert as element."""
        text = self.intro_text.get(self.path_str)
        if text:
            self.create_element('intro_text', text)

    def new_section(self, title, numbering=True, **kw):
        """Create and Return new child Section (subsection)."""
        new_section = type(self)(name=title, elements={}, parent=self, **kw)
        new_section.elements['title'] = rls.Element.from_content(title, heading=True, numbering=numbering, level=self.depth+1)
        new_section.insert_intro_text()
        return new_section


def round_if_float(x, decimals=1):
    # if x == '50.000000':
    #     print(float(x), float(x).is_integer(), int(x))

    if isinstance(x, float):
        return round(x, decimals)
    else:

        try:
            # print(x, float(x).is_integer(), int(x))
            if not float(x).is_integer():
                return round(float(x), decimals)
            else:
                return int(float(x))
        except (ValueError, TypeError):
            # print(x)
            return x

        
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
        'lan': 'LAN',
        'wan': 'WAN',

        'waketime': 'Wake Time (s)',
        'nits': 'Avg Luminance (Nits)',
        'limit': 'Power Limit (W)',
        'watts': 'Avg Power (W)',
        'ratio': 'Power/Power Limit',
        'result': 'Result',
    }
    if cols is None:
        cols = [col for col in rename_cols.keys() if col in rsdf.columns]
    cdf = rsdf[cols].copy()
    if 'test_time' in cdf.columns:
        cdf['test_time'] = cdf['test_time'].astype(int)
    if 'video' in cdf.columns:
        cdf['video'] = cdf['video'].apply(lambda x: rename_video.get(x, x))
    if 'lux' in cdf.columns:
        # cdf['lux'] = cdf['lux'].astype(object)
        cdf['lux'] = cdf['lux'].fillna(-1).astype(int).astype(str).replace('-1', '')

    cdf = cdf.dropna(axis=1, how='all')
    cdf = cdf.rename(columns=rename_cols)


    cdf = cdf.applymap(round_if_float)
    return cdf


def get_title_page(report_title, model):
    """Wrap title page function to support title and model variables"""
    if report_title is None:
        report_title = 'TV Power Measurement Report'
    def title_page(canvas, doc):
        """Create a custom title page for the reportlab pdf doc."""
        canvas.saveState()
    
        pcl_logo_width, pcl_logo_height = 1.33*inch*1.35, 1.43*inch*1.35
        pcl_logo_x = 306 - pcl_logo_width/2
        pcl_logo_y = 2*inch
        pcl_logo_path = Path(sys.path[0]).joinpath(r'img\pcl-logo.jpg')
        canvas.drawImage(pcl_logo_path, pcl_logo_x, pcl_logo_y, width=pcl_logo_width, height=pcl_logo_height,
                         preserveAspectRatio=True)
    
        neea_logo_width, neea_logo_height = 1.24*inch, .82*inch
        neea_logo_y = 5*inch
        neea_logo_x = 306 - neea_logo_width/2
        neea_logo_path = Path(sys.path[0]).joinpath(r'img\neea.png')
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
    """Style (highlight) on mode compliance table based on content (pass/fail results)."""
    # todo implement estar boolean (report_type
    
    style = []
    for i, row in on_mode_df.iterrows():
        if row['test_name']=='average_measured' and 'ratio' in on_mode_df.columns:
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
        elif 'result' in on_mode_df.columns:
            color = 'green' if row['result'] == 'Pass' else 'red'
            style.append(('BACKGROUND', (-1, i + 1), (-1, i + 1), color))

    if report_type != 'estar':
        style += [('BACKGROUND', (0, -1), (-2, -1), 'lightgrey')]

    style += [
        ('BACKGROUND', (0, 0), (-1, 0), 'lightgrey'),
        ('FONTNAME', (0, 0), (-1, -1), 'Calibri'),
        ('BOX', (0, 0), (-1, -1), 1.0, 'black'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER')
    ]
    if report_type == 'estar':
        break_lines = list(range(len(on_mode_df)))
    else:
        break_lines = [i + 1 for i, test_name in on_mode_df['test_name'].iteritems() if 'measured' in test_name]
    for i in break_lines:
        style.append(('BOX', (0, 1), (-1, i), 1.0, 'black'))
    return style


def standby_df_style(standby_df):
    """Style (highlight) standby compliance table based on content (pass/fail results)."""
    style = []
    for i, val in standby_df['result'].iteritems():
        if val=='Pass':
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


def compliance_summary_df_style(csdf):
    """Style (highlight) standby compliance table based on content (pass/fail results)."""
    style = []
    for i, row in csdf.iterrows():
        if row['test_name'] == 'average_measured' or 'measured' not in row['test_name']:
            color = 'green' if row['result'] == 'Pass' else 'red'
            style.append(('BACKGROUND', (-1, i + 1), (-1, i + 1), color))
        

    style += [
        ('BACKGROUND', (0, 0), (-1, 0), 'lightgrey'),
        ('FONTNAME', (0, 0), (-1, -1), 'Calibri'),
        ('BOX', (0, 0), (-1, -1), 1.0, 'black'),
        # ('GRID', (0, 0), (-1, -1), .25, 'black'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT')
    ]
    if 'average_measured' not in csdf['test_name'].values:
        break_lines = list(range(len(csdf)))
    else:
        first_bl = [i + 1 for i, test_name in csdf['test_name'].iteritems() if test_name=='average_measured'][0]
        break_lines = list(range(first_bl, len(csdf)))
    for i in break_lines:
        style.append(('BOX', (0, 1), (-1, i), 1.0, 'black'))
    return style


def get_limit_func_strings(limit_funcs, hdr):
    """Create strings to display the power limit functions within report."""
    def get_func_str(limit_func):
        coeffs = limit_func.keywords
        func_str = f"adjustment_factor*{coeffs['sf']:.2f}*(({coeffs['a']:.3f}*area+{coeffs['b']:.2f})*luminance + {coeffs['c']:.2f}*area + {coeffs['d']:.2f})"
        if 'power_cap_func' in coeffs.keys():
            pcf = coeffs['power_cap_func'].keywords
            power_cap_func_str = f"adjustment_factor*{pcf['sf']:.2f}*(({pcf['a']:.3f}*area)+{pcf['b']:.3f})"
            func_str = f'Minimum of:<br/>• {func_str}<br/>• {power_cap_func_str}'
        return func_str
    lfs = {
        'default': '<strong>Default PPS Power Limit Function</strong><br/>' + get_func_str(limit_funcs['default']),
        'brightest': '<strong>Brightest PPS Power Limit Function</strong><br/>' + get_func_str(limit_funcs['brightest']),
        'hdr': '<strong>HDR Default PPS Power Limit Function</strong><br/>' + get_func_str(limit_funcs['hdr10'])
    }
    return lfs




@skip_and_warn
def add_persistence_summary(report, persistence_dfs, **kwargs):
    """Add section displaying persistence tables found in entry forms (for PCL testing only)"""
    if persistence_dfs is not None:
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
def add_compliance_section(report, merged_df, report_type, omit_estar, estar_on_mode_df, va_on_mode_df,
                           estar_limit_funcs, va_limit_funcs, hdr, rsdf, area, standby_df,
                           waketimes, adjustment_factor, **kwargs):

    with report.new_section('Compliance', page_break=False) as cat:
        with cat.new_section('Standby Summary', page_break=False) as standby_summary:
            @skip_and_warn
            def add_compliance_summary_standby(report):
                table_df = clean_rsdf(standby_df, standby_df.columns)
                rename_tests = {
                    'standby_passive': 'P<sub rise=2>STANDBY-PASSIVE</sub>',
                    'standby_google': 'P<sub rise=2>GOOGLE-STANDBY-ACTIVE-LOW</sub>',
                    'standby_echo': 'P<sub rise=2>AMAZON-STANDBY-ACTIVE-LOW</sub>',
                    'standby_multicast': 'P<sub rise=2>MDNS-STANDBY-ACTIVE-LOW</sub>',
                    'standby': 'P<sub rise=2>STANDBY-ACTIVE-LOW</sub>',
                    'standby_active_low': 'P<sub rise=2>STANDBY-ACTIVE-LOW</sub>',
                
                }
                table_df.insert(0, 'Measurement', table_df['Test Name'].apply(rename_tests.get))
                standby_summary.create_element('table', table_df, grid_style=standby_df_style(standby_df))
        
            add_compliance_summary_standby(report)
            with standby_summary.new_section('Standby Chart') as standby_chart:
                @skip_and_warn
                def add_standby_chart(report):
                    standby_tests = [test for test in rsdf.test_name.unique() if 'standby' in test]
                    # time vs power (line) plot showing all standby tests
                    standby_chart.create_element('standby_plot', plots.standby(merged_df, standby_tests))
    
                add_standby_chart(report)
        @skip_and_warn
        def add_compliance_summary_on_mode(report, section, limit_type, limit_funcs, on_mode_df):
        
            table_df = clean_rsdf(on_mode_df, cols=on_mode_df.columns)
        
            style = on_mode_df_style(on_mode_df, limit_type)
            if limit_type != 'estar':
                rename_tests = {
                    'default': 'P<sub rise=2>oa_Default_ABC_Off</sub>',
                    'default_100': 'P<sub rise=2>oa_Default_100Lux</sub>',
                    'default_35': 'P<sub rise=2>oa_Default_35Lux</sub>',
                    'default_12': 'P<sub rise=2>oa_Default_12Lux</sub>',
                    'default_3': 'P<sub rise=2>oa_Default_3Lux</sub>',
                    'default_measured': 'P<sub rise=2>oa_Default</sub>',
                
                    'brightest': 'P<sub rise=2>oa_Brightest_ABC_Off</sub>',
                    'brightest_100': 'P<sub rise=2>oa_Brightest_100Lux</sub>',
                    'brightest_35': 'P<sub rise=2>oa_Brightest_35Lux</sub>',
                    'brightest_12': 'P<sub rise=2>oa_Brightest_12Lux</sub>',
                    'brightest_3': 'P<sub rise=2>oa_Brightest_3Lux</sub>',
                    'brightest_measured': 'P<sub rise=2>oa_Brightest</sub>',
                
                    'hdr10': 'P<sub rise=2>oa_HDR10_ABC_Off</sub>',
                    'hdr10_100': 'P<sub rise=2>oa_HDR10_100Lux</sub>',
                    'hdr10_35': 'P<sub rise=2>oa_HDR10_35Lux</sub>',
                    'hdr10_12': 'P<sub rise=2>oa_HDR10_12Lux</sub>',
                    'hdr10_3': 'P<sub rise=2>oa_HDR10_3Lux</sub>',
                    'hdr10_measured': 'P<sub rise=2>oa_HDR10</sub>',
                    'average_measured': 'P<sub rise=2>oa_Average</sub>'
                }
            
                table_df.insert(0, 'Measurement', table_df['Test Name'].apply(rename_tests.get))
                if 'default_100' not in table_df['Test Name'].values:
                    table_df = table_df.replace(
                        {'P<sub rise=2>oa_Default_ABC_Off</sub>': 'P<sub rise=2>oa_Default</sub>'})
                if 'brightest_100' not in table_df['Test Name'].values:
                    table_df = table_df.replace(
                        {'P<sub rise=2>oa_Brightest_ABC_Off</sub>': 'P<sub rise=2>oa_Brightest</sub>'})
                if 'hdr10_100' not in table_df['Test Name'].values:
                    table_df = table_df.replace({'P<sub rise=2>oa_HDR10_ABC_Off</sub>': 'P<sub rise=2>oa_HDR10</sub>'})
                # table_df = table_df.rename(columns={'Test Name': ''})
                table_df = table_df.replace(
                    {'default_measured': '', 'brightest_measured': '', 'hdr10_measured': '', 'average_measured': ''})
            else:
                rename_tests = {
                    'default': 'P<sub rise=2>on_Default</sub>',
                    'brightest': 'P<sub rise=2>on_Brightest</sub>',
                    'hdr10': 'P<sub rise=2>on_HDR10</sub>',
                }
                table_df.insert(0, 'Measurement', table_df['Test Name'].apply(rename_tests.get))
            section.create_element('on mode table', table_df, grid_style=style)
        
            if limit_type == 'estar':
                # todo: implement estar text
                #   probably dependent on how get_on_mode_df implements
                #   potentially include within same function
                pass
            else:
                text = "P<sub rise=2>oa_Average</sub> is the average Power/Power Limit of P<sub " \
                       "rise=2>oa_Default</sub>, P<sub rise=2>oa_Brightest</sub>, and P<sub rise=2>oa_HDR10</sub> " \
                       "(if applicable). P<sub rise=2>oa_Average</sub> must be less than 1.0 to comply. "
                section.create_element('text', text)
            s = f'TV Area: {area} sq. in.<br />Adjustment Factor: {adjustment_factor}'
            section.create_element('compliance paramaters', s)
            adjustment_factor_df = pd.DataFrame(data=[
                ['HD', '0.75'],
                ['4K', '1'],
                ['4K_HCR', '1.25'],
                ['8K', '1.5']
            ], columns=['Adjustment Factor', 'Value'])
        
            section.create_element('adjustment factor header', '<strong>Adjustment Factor Values</strong><br/>')
            section.create_element('adjustment factor table', adjustment_factor_df, colWidths=[90, 135],
                                   hAlign='LEFT')
        
            # display power limit functions below on mode table
            limit_func_strings = get_limit_func_strings(limit_funcs, hdr)
            section.create_element('default limit function', limit_func_strings['default'])
            section.create_element('brightest limit function', limit_func_strings['brightest'])
            if hdr:
                section.create_element('hdr limit function', limit_func_strings['hdr'])

        @skip_and_warn
        def add_on_mode_charts(report, section, limit_funcs):
            # add scatter plot for each pps showing tv power measurements in relation to the relevant limit function line
            for pps in ['default', 'brightest']:
                section.create_element(
                    f'{pps} dimming plot',
                    plots.dimming_line_scatter(pps, rsdf, area, limit_funcs)
                )
            if hdr:
                section.create_element(
                    'hdr dimming plot',
                    plots.dimming_line_scatter('hdr10', rsdf, area, limit_funcs)
                )
            
        if report_type!='estar':
            with cat.new_section('VA On Mode Summary') as on_mode_summary:
                    # on_mode_summary.create_element('adjustment factor table', adjustment_factor_df)
                add_compliance_summary_on_mode(report, on_mode_summary, 'alternative', va_limit_funcs, va_on_mode_df)
                with on_mode_summary.new_section('VA On Mode Charts') as on_mode_charts:
                    add_on_mode_charts(report, on_mode_charts, va_limit_funcs)
        if not omit_estar:
            with cat.new_section('ENERGY STAR On Mode Summary') as estar_on_mode_summary:
                add_compliance_summary_on_mode(report, estar_on_mode_summary, 'estar', estar_limit_funcs, estar_on_mode_df)
                with estar_on_mode_summary.new_section('ENERGY STAR On Mode Charts') as estar_on_mode_charts:
                    add_on_mode_charts(report, estar_on_mode_charts, estar_limit_funcs)
            
        with cat.new_section('All On Mode Tests Chart') as all_tests_chart:
            all_tests_chart.create_element('all dimming lines plot', plots.all_dimming_lines(rsdf))
            

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
def add_light_directionality(report, lum_df, **kwargs):
    with report.new_section("Average Luminance Along TV's Horizontal Axis", numbering=False) as x_nits:
        x_nits.create_element('x nits plot', plots.x_nits(lum_df))
    with report.new_section("Average Luminance Along TV's Vertical Axis", numbering=False) as y_nits:
        y_nits.create_element('y nits plot', plots.y_nits(lum_df))
    with report.new_section('Luminance Heatmap', numbering=False) as heatmap:
        heatmap.create_element('heatmap', plots.nits_heatmap(lum_df))
    return report

@skip_and_warn
def add_overlay(report, rsdf, merged_df, test_names, **kwargs):
    # table and line plot showing stabilization tests
    table_df = clean_rsdf(rsdf.query('test_name.isin(@test_names)'))
    report.create_element('table', table_df)
    report.create_element('plot', plots.overlay(merged_df, test_names))

@skip_and_warn
def add_supplemental(report, rsdf, merged_df, hdr, lum_df, spectral_df, scdf, washout_df, washout_crossovers,
                     color_shift_df, color_shift_crossovers, brightness_loss_df, brightness_loss_crossover, **kwargs):
    with report.new_section('Supplemental Test Results', page_break=False) as supp:
        with supp.new_section('Stabilization') as stab:
            stab_tests = [test for test in rsdf.test_name.unique() if 'stabilization' in test]
            stab = add_overlay(stab, rsdf, merged_df, stab_tests)
        
        with supp.new_section("APL' vs Power Charts", page_break=False)as apl_power:
            # APL vs power scatter plots for each pps (w/ line of best fit)
            apl_power = add_apl_power(apl_power, 'default', merged_df, rsdf, section_name='Default PPS: SDR')
            apl_power = add_apl_power(apl_power, 'brightest', merged_df, rsdf, section_name='Brightest PPS: SDR')
            if hdr:
                apl_power = add_apl_power(apl_power, 'hdr10', merged_df, rsdf, section_name='Default PPS: HDR')
        with supp.new_section('Light Directionality', page_break=False) as ld:
            ld = add_light_directionality(ld, lum_df)
        
        if spectral_df is not None:
            @skip_and_warn
            def add_spectral_power_distribution(report):
                with supp.new_section('Spectral Power Distribution') as spd:
                    spd.create_element('spectral plot', plots.spectral_power_distribution(spectral_df))
                    spd.create_element('cheap page break', '<br /><br /><br /><br /><br /><br /><br /><br /><br /><br />')
                    spd.create_element('chromaticity plot', plots.chromaticity(spectral_df))
                    spd.create_element('spectral coordinates table', scdf)
                    text = f" BT.2020 Colorspace Coverage: {100*kwargs['bt2020_coverage']:.0f}%<br /> BT.709 Colorspace Coverage: {100*kwargs['bt709_coverage']:.0f}%"
                    spd.create_element('coverage', text)
            add_spectral_power_distribution(report)
            @skip_and_warn
            def add_viewing_angle(report):
                with supp.new_section('Viewing Angle Tests') as vat:
                    vat.create_element('color washout plot', plots.color_washout(washout_df))
                    text = '80% Crossovers:<br/><br/>'
                    for color, crossover in washout_crossovers.items():
                        if crossover is not None:
                            text += f'{color}: {round(crossover, 1)}<br/>'
                    vat.create_element('washout crossovers', text)
                    
                    vat.create_element('color shift plot', plots.color_shift(color_shift_df))
                    if any(color_shift_crossovers['positive'].values()):
                        text = '3° Crossovers: <br/>'
                        for color, crossover in color_shift_crossovers['positive'].items():
                            if crossover is not None:
                                text += f'{color}: {round(crossover, 1)}<br/>'
                    if any(color_shift_crossovers['negative'].values()):
                        text += '<br/>-3° Crossovers: <br/>'
                        for color, crossover in color_shift_crossovers['negative'].items():
                            if crossover is not None:
                                text += f'{color}: {round(crossover, 1)}<br/>'
                    if text:
                        vat.create_element('color shift crossovers', text)
                    vat.elements['color shift page break'] = [PageBreak()]
                    vat.create_element('brightness loss plot', plots.brightness_loss(brightness_loss_df))
                    text = f'75% Crossover: {round(brightness_loss_crossover, 1)}'
                    vat.create_element('brightness loss crossover', text)
            add_viewing_angle(report)
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
    with report.new_section('Plots of All Tests', page_break=False) as trp:
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

        test_specs.create_element('test spec table', test_specs_df.reset_index().applymap(round_if_float), grid_style=style, header=False)
    return report

@skip_and_warn
def add_appendix(report, setup_img_paths, bar3_lum_df, **kwargs):
    with report.new_section('Appendix', page_break=False) as app:
        with app.new_section('Setup Images') as sui:
            for i, path in enumerate(setup_img_paths):
                sui.create_element(f'setup imgae {i}', path)
        with app.new_section('3bar Luminance Table') as b3:
            b3.create_element('table', bar3_lum_df)
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
    with open(ff.APPDATA_DIR.joinpath('report-location.txt'), 'w') as f:
        f.write(path_str)
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
    report = add_appendix(report, **report_data)
    filename = {'estar': 'ENERGYSTAR-report.pdf',
                   'alternative': 'va-report.pdf',
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
