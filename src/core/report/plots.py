from collections import OrderedDict
from functools import partial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import rcParams, transforms
import matplotlib.lines as mlines
from seaborn import heatmap
from colour.models import BT2020_COLOURSPACE, BT709_COLOURSPACE
from colour.colorimetry.spectrum import SpectralDistribution
from colour.plotting import plot_sds_in_chromaticity_diagram_CIE1931
from colour.plotting import plot_RGB_colourspaces_in_chromaticity_diagram_CIE1931

rcParams['font.family'] = "sans-serif"
rcParams['font.sans-serif'] = "Calibri"

def format_ax(ax=None, xlabel='Time (s)', ylabel='Power (W)'):
    if not ax:
        ax = plt.gca()
    ax.set_facecolor('whitesmoke')
    ax.set_xlabel(xlabel, fontsize=20)
    ax.set_ylabel(ylabel, fontsize=20)
    ax.tick_params(labelsize=14)


def time_series(series_list, labels=None, colors=None, ax=None, show_avg=True, **kwargs):
    if not ax:
        ax = plt.gca()
    if not colors:
        colors = [None] * len(series_list)
    format_ax(ax, **kwargs)
    for series, color in zip(series_list, colors):
        ax.plot(series, color=color)
    # make sure y axis range is at least 1
    ymin, ymax = ax.get_ylim()
    yrange = ymax - ymin
    ymid = ymin + yrange/2
    if yrange < 1:
        ax.set_ylim(bottom=ymid-.5, top=ymid+.5)

    if len(series_list) == 1 & show_avg:
        avg = round(series.mean(), 1)
        s = 'Avg: {}'.format(avg)
        ax.text(.9, .9, s, fontsize=14, transform=ax.transAxes)
    elif labels:
        ax.legend(labels=labels, fontsize=14)


def standard(tdf):
    fig, axes = plt.subplots(4, 1, figsize=(12.2, 15), sharex=True)
    fig.tight_layout(h_pad=-1)

    cols = ['nits', 'watts', "APL'"]
    ylabels_dict = {
        'nits': 'Luminance (Nits)',
        'watts': 'Power (W)',
        "APL'": "APL' (%)"
    }
    colors = ['lightcoral', 'black', 'darkorange']
    if 'standby' in tdf['test_name'].iloc[0]:
        show_avg = False
    else:
        show_avg = True
    for col, color, ax in zip(cols, colors, axes[:3]):
        ylabel = ylabels_dict.get(col, col)
        time_series([tdf[col]], colors=[color], ax=ax, ylabel=ylabel, show_avg=show_avg)

    series_list = [tdf[col] for col in 'RGB']
    time_series(series_list, colors=['red', 'green', 'blue'], ax=axes[3], ylabel='RGB (Nits)')

    fig.subplots_adjust(left=.08, bottom=.05)
    plt.close()
    return fig


def overlay(df, test_names):
    fig, ax = plt.subplots(figsize=(10, 7))
    series_list, labels = [], []
    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:cyan', 'tab:pink']
    averages = []

    for i, test in enumerate(test_names):
        tdf = df.query('test_name==@test').reset_index()
        series_list.append(tdf['watts'])
        labels.append(test)
        avg = round(tdf['watts'].mean(), 1)
        averages.append(avg)
        s = 'Avg: {}'.format(avg)
        ax.text(.8, .2 - .05 * i, s, fontsize=14, color=colors[i], transform=ax.transAxes)

    pct_diff = round(100 * ((averages[-1] - averages[-2]) / averages[-2]), 1)
    s = 'Difference: {}%'.format(pct_diff)
    ax.text(.8, .2 - .05 * (i + 1), s, fontsize=14, color='black', transform=ax.transAxes)
    time_series(series_list, labels=labels, ylabel='Power (W)', colors=colors)
    plt.close()
    return fig


def standby(df, test_names):
    fig, ax = plt.subplots(figsize=(12, 10))
    fig.tight_layout(h_pad=-2)
    watts_series_list = []
    handles = []
    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:cyan', 'tab:pink']
    for i, test in enumerate(test_names):
        tdf = df[df['test_name'] == test].reset_index().iloc[13:-30]
        watts_series_list.append(tdf['watts'])
        if 'qs' in df.columns:
            label = test
            color = colors[i]

            handle = mlines.Line2D([], [], linewidth=2, color=color, label=label)
            handles.append(handle)

    time_series(watts_series_list, ylabel='Power (W)', show_avg=False)

    ax.legend(handles=handles, fontsize=14)

    fig.subplots_adjust(left=.08, bottom=.06)
    plt.close()
    return fig


# def standby_bar(stby_df):
#     fig, ax = plt.subplots(figsize=(10, 10))
#
#     ax.bar(x=stby_df.test_name, height=stby_df.watts, color='tab:blue')
#     format_ax(ax=ax, xlabel=None, ylabel='Avg. Power (W)')
#     custom_red = (.75,0,0)
#     ax.plot(ax.get_xlim(), (2, 2), color=custom_red, linestyle='dashed')
#     red_dashed_line = mlines.Line2D([], [], linewidth=2, linestyle='dashed', color=custom_red, label='Standby Limit')
#     ax.legend(handles=[red_dashed_line])
#     plt.close()
#     return fig


def apl_watts_scatter(df, test_names):
    '''makes scatter plot of APL (x axis) vs Watts (y axis) for a single test
    also plots a natural log curve of best fit'''
    fig, ax = plt.subplots(figsize=(10, 10))
    tdf = df[df['test_name'] == test_names].copy()

    format_ax(ax, xlabel="APL' (%)", ylabel='Power (W)')
    ax.scatter(tdf["APL'"], tdf['watts'])

    # change 0 APL to .1 to avoid errors in polyfit function
    for i in list(tdf[tdf["APL'"] <= 0].index):
        tdf.loc[i, "APL'"] = .1
    
    try:
        # this sometimes throws an SVD did not converge error the first time it's run but not the second??
        a, b = np.polyfit(tdf["APL'"].values, tdf['watts'].values, 1)
    except:
        a, b = np.polyfit(tdf["APL'"].values, tdf['watts'].values, 1)

    ax.plot(sorted(tdf["APL'"]), a * np.array((sorted(tdf["APL'"]))) + b, color='red')
    #     settings = ['video', 'preset_picture', 'abc', 'mdd']
    #     settings_box(settings, tdf)

    text = 'y = {}x + {}'.format(round(a, 1), round(b, 1))
    ax.text(.7, .1, text, transform=ax.transAxes, fontsize=14)
    #     fig.suptitle('APL\' vs Watts', fontsize=24)
    plt.close()
    return fig


# def limit_ratio(on_mode_df):
#     mask = on_mode_df['test_name'].apply(lambda name: 'measured' in name)
#     limit_ratio_df = on_mode_df[mask].dropna(subset=['watts']).copy()
#     limit_ratio_df['limit_ratio'] = limit_ratio_df['watts']/limit_ratio_df['limit']
#     xlabel_dict = {
#         'default_measured': 'Default PPS',
#         'brightest_measured': 'Brightest PPS',
#         'hdr_measured': 'HDR10 Default PPS'
#     }
#     limit_ratio_df['name'] = limit_ratio_df['test_name'].apply(xlabel_dict.get)
#     avg = {
#         'name': 'Average',
#         'limit_ratio': limit_ratio_df['limit_ratio'].mean()
#     }
#     limit_ratio_df = limit_ratio_df.append(avg, ignore_index=True)
#
#     fig, ax = plt.subplots(figsize=(10, 10))
#     plt.bar(x=limit_ratio_df['name'], height=limit_ratio_df['limit_ratio'], color=['tab:blue']*3+['tab:orange'])
#     plt.xlim(*plt.xlim())
#     plt.plot(plt.xlim(), (1,1), linestyle='dashed', color='red')
#     format_ax(xlabel='', ylabel='Measured Power/Limit')
#     plt.title('Compliance', fontsize=24)
#     plt.close()
#     return fig


def dimming_line_scatter(pps, rsdf, area, limit_funcs):
    def get_points(pps, rsdf):
        label_dict = {
            'default': {
                'default': 'ABC Off',
                'default_100': '100 Lux',
                'default_35': '35 Lux',
                'default_12': '12 Lux',
                'default_3': '3 Lux',
                'default_low_backlight': 'Minimum Backlight',
            },
            'brightest': {
                'brightest': 'ABC Off',
                'brightest_100': '100 Lux',
                'brightest_35': '35 Lux',
                'brightest_12': '12 Lux',
                'brightest_3': '3 Lux',
                'brightest_low_backlight': 'Minimum Backlight',
            },
            'hdr10': {
                'hdr10': 'ABC Off',
                'hdr10_100': '100 Lux',
                'hdr10_35': '35 Lux',
                'hdr10_12': '12 Lux',
                'hdr10_3': '3 Lux',
                'hdr10_low_backlight': 'Minimum Backlight'
            }
        }
        mask = rsdf['test_name'].apply(lambda name: name in label_dict[pps])
        cdf = rsdf[mask].copy()
        cdf['label'] = cdf['test_name'].apply(label_dict[pps].get)
        points = dict(zip(cdf['label'], zip(cdf['nits'], cdf['watts'])))
        return points

    points = get_points(pps, rsdf)

    limit_func = limit_funcs.get(pps)

    fig, ax = plt.subplots(figsize=(10, 10))
    format_ax(ax=ax, xlabel='Luminance (Nits)', ylabel='Power (W)')

    ordered_points = OrderedDict(sorted(points.items(), key=lambda i: i[1][0]))
    lums = [point[0] for label, point in points.items() if label != 'Measured']
    pwrs = [point[1] for label, point in points.items() if label != 'Measured']
    plt.plot(lums, pwrs, color='tab:blue')
    markersize = 10
    markers = {
        'ABC Off': 'P',
        '100 Lux': '^',
        '35 Lux': '<',
        '12 Lux': '>',
        '3 Lux': 'v',
        'Minimum Backlight': 'v',
    }
    handles = []
    for label, point in reversed(ordered_points.items()):
        plt.plot(*point, marker=markers[label], color='tab:blue', markersize=markersize)
        handle = mlines.Line2D([], [], linewidth=0, label=label, marker=markers[label], markersize=markersize)
        handles.append(handle)

    abc_on_lums = [point[0] for label, point in points.items() if label != 'ABC Off']
    abc_on_power = [point[1] for label, point in points.items() if label not in ['ABC Off', 'Minimum Backlight']]
    if abc_on_power:
        abc_on = tuple(np.mean([abc_on_lums, abc_on_power], axis=1))
        measured = tuple(np.mean([points['ABC Off'], abc_on], axis=0))
        plt.plot(*measured, marker='o', color='black', markersize=markersize)
        pps_label = pps.title() if pps != 'hdr10' else pps.upper()
        handle = mlines.Line2D([], [], linewidth=0, label=f'Poa_{pps_label}', marker='.', markersize=markersize, color='black')
        handles.append(handle)

    min_lum, max_lum = 0, max(lums)*1.25
    
    if 'power_cap_func' in limit_func.keywords:
        lum_bend = 0
        prev_lim, new_lim = limit_func(area, luminance=lum_bend-1), limit_func(area, luminance=lum_bend)
        while new_lim > prev_lim:
            prev_lim = new_lim
            lum_bend += 1
            new_lim = limit_func(area, luminance=lum_bend)
        
        max_lum = max(max_lum, lum_bend*1.25)
    
    xs = np.arange(min_lum, max_lum, .1)
    ys = [limit_func(area=area, luminance=i) for i in xs]
    plt.plot(xs, ys, color='tab:orange')
    
    handle = mlines.Line2D([], [], linewidth=1, label=f'Power Limit', color='tab:orange')
    handles.append(handle)

    plt.xlim(min_lum, max_lum)
    ax.legend(handles=handles)
    title = {'default': 'Compliance Chart: Default PPS', 'brightest': 'Compliance Chart: Brightest PPS', 'hdr': 'Compliance Chart: HDR Default PPS'}.get(pps)
    plt.title(title, fontsize=24)
    plt.close()
    return fig


def x_nits(light_df):
    xs = light_df.mean(axis=0)
    fig = xs.plot(figsize=(12, 8)).get_figure()
    format_ax(ax=fig.get_axes()[0], xlabel='Distance From Left Edge \n(% of TV Width)', ylabel='Avg Luminance\n(Nits)')

    plt.close()
    return fig


def y_nits(light_df):
    # light_df.to_csv('light_df.csv')
    ys = light_df.mean(axis=1)
    ys.index = map(lambda x: x - 100, reversed(ys.index))
    base = plt.gca().transData
    rot = transforms.Affine2D().rotate_deg(-90)
    fig = ys.plot(figsize=(8, 12), legend=False, transform=rot + base, ylim=(0, 100), xlim=(0, max(ys)*1.05)).get_figure()
    format_ax(ax=fig.get_axes()[0], ylabel='Distance From Bottom Edge\n(% of TV Height)',
              xlabel='Avg Luminance\n(Nits)')
    # plt.savefig('y-nits-plot.png')
    plt.close()
    # plt.show()
    return fig


def nits_heatmap(light_df):
    fig, ax = plt.subplots(figsize=(19.2/1.5, 10.8/1.5))
    format_ax(ax=ax, xlabel='Distance From Left Edget', ylabel='Distance From Bottom Edge')
    a = np.array(light_df).ravel()
    vmax = np.percentile(a, 95)
    heatmap(light_df, ax=ax, vmin=0, vmax=vmax)
    ax.collections[0].colorbar.set_label('Luminance\n(Nits)', fontsize=16)
    y_count, x_count = light_df.shape
    ax.set_xticks(range(0, x_count+1, int(x_count/10)))
    ax.set_xticklabels(range(0, 101, 10))
    xlabel = 'Distance From Left Edge \n(% of TV Width)'

    ax.set_yticks(range(0, y_count+1, int(y_count/10)))
    ax.set_yticklabels(range(100, -1, -10))
    ylabel = 'Distance From Bottom Edge\n(% of TV Height)'
    format_ax(xlabel=xlabel, ylabel=ylabel)
    ax.spines['bottom'].set_color('0.5')
    ax.spines['top'].set_color('0.5')
    ax.spines['right'].set_color('0.5')
    ax.spines['left'].set_color('0.9')
    fig.subplots_adjust(top=.97, bottom=.14, right=.99)
    plt.close()
    return fig


def spectral_power_distribution(spectral_df):
    spectral_df.plot(color=['white', 'red', 'green', 'blue'], figsize=(10, 7))
    
    format_ax(xlabel='Wavelength (nm)', ylabel='Radiance\n(W·$sr^{-1}·m^{−2}$)')
    ax = plt.gca()
    ax.set_facecolor('dimgray')
    fig = plt.gcf()
    fig.subplots_adjust(top=.97, left=.15, right=.99)
    plt.close()
    return fig


def chromaticity(spectral_df):
    sd_list = [SpectralDistribution(spectral_df[color], name=color) for color in spectral_df.columns]
    callable = partial(plot_sds_in_chromaticity_diagram_CIE1931, sd_list)
    colour_spaces = [BT2020_COLOURSPACE, BT709_COLOURSPACE]
    fig, ax = plot_RGB_colourspaces_in_chromaticity_diagram_CIE1931(
        colourspaces=colour_spaces,
        chromaticity_diagram_callable_CIE1931=callable,
        standalone=False
    )
    fig.set_size_inches(10, 7)
    ax.legend(handles=ax.legend().legendHandles[-2:])
    format_ax(xlabel='CIE X', ylabel='CIE Y')
    ax.set_title('CIE 1931 2 Degree Standard Observer', fontsize=24)
    plt.close()
    return fig