# import re
import numpy as np
# import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import matplotlib.lines as mlines
# from matplotlib import transforms
# import seaborn as sns
# from scipy.stats import pearsonr
# import tables

# Set matplotlib font.
matplotlib.rcParams['font.family'] = "sans-serif"
matplotlib.rcParams['font.sans-serif'] = "Calibri"

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


def stabilization(df, test_names):
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


def standby_bar(stby_df):
    fig, ax = plt.subplots(figsize=(10, 10))

    ax.bar(x=stby_df.test_name, height=stby_df.watts, color='tab:blue')
    format_ax(ax=ax, xlabel=None, ylabel='Avg. Power (W)')
    custom_red = (.75,0,0)
    ax.plot(ax.get_xlim(), (2, 2), color=custom_red, linestyle='dashed')
    red_dashed_line = mlines.Line2D([], [], linewidth=2, linestyle='dashed', color=custom_red, label='Standby Limit')
    ax.legend(handles=[red_dashed_line])
    plt.close()
    return fig


def apl_watts_scatter(df, test_names):
    '''makes scatter plot of APL (x axis) vs Watts (y axis) for a single test
    also plots a natural log curve of best fit'''
    fig, ax = plt.subplots(figsize=(10, 10))
    tdf = df[df['test_name'] == test_names].copy()

    format_ax(ax, xlabel="APL' (%)", ylabel='Power (W)')
    ax.scatter(tdf["APL'"], tdf['watts'])

    # change 0 APL to .1 to avoid errors in polyfit function
    for i in list(tdf[tdf["APL'"] == 0].index):
        tdf.loc[i, "APL'"] = .1

    a, b = np.polyfit(tdf["APL'"], tdf['watts'], 1)
    ax.plot(sorted(tdf["APL'"]), a * np.array((sorted(tdf["APL'"]))) + b, color='red')
    #     settings = ['video', 'preset_picture', 'abc', 'mdd']
    #     settings_box(settings, tdf)

    text = 'y = {}x + {}'.format(round(a, 1), round(b, 1))
    ax.text(.7, .1, text, transform=ax.transAxes, fontsize=14)
    #     fig.suptitle('APL\' vs Watts', fontsize=24)
    plt.close()
    return fig