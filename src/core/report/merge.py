import datetime
import sys
from pathlib import Path
import numpy as np
import pandas as pd


APL_FILES = {
    'sdr': r'config\apl\sdr-APL.csv',
    'clasp_hdr': r'config\apl\clasp_hdr10-APL.csv',
}

def round_time(dt=None, date_delta=datetime.timedelta(seconds=1)):
    """Round a datetime object to a multiple of a timedelta
    dt : datetime.datetime object, default now.
    date_delta : timedelta object, we round to a multiple of this, default 1 minute.
    Author: Thierry Husson 2012 - Use it as you want but don't blame me.
            Stijn Nevens 2014 - Changed to use only datetime objects as variables
    """
    roundTo = date_delta.total_seconds()

    if dt == None: dt = datetime.datetime.now()
    seconds = (dt.to_pydatetime() - dt.min).seconds
    # // is a floor division, not a comment on following line:
    rounding = (seconds + roundTo / 2) // roundTo * roundTo
    return dt + datetime.timedelta(0, rounding - seconds, -dt.microsecond)


def clean_tag(tag):
    """Reformats stabilization tags into numbers"""
    if 'stabilization' in str(tag):
        tag = '{}.{}'.format(tag[0], tag[-1])
        return float(tag)
    elif 'user command' in str(tag):
        return np.nan
    else:
        return float(tag)


def add_stab_tests(test_seq_df, df):
    """Add a row to test_seq_df for each stabilization test in data_df"""
    stab_row = test_seq_df[test_seq_df['test_name'] == 'stabilization'].iloc[0]
    stab_tags = df[(df['Tag'] > stab_row['tag']) & (df['Tag'] < stab_row['tag']+1)]['Tag'].unique()
    df_list = []
    for i, tag in enumerate(stab_tags):
        new_row = stab_row.copy().to_frame().T
        new_row['test_time'] = len(df[df['Tag'] == tag])
        new_row['tag'] = tag
        new_row['test_name'] = f'stabilization{i+1}'
        df_list.append(new_row)
    if df_list:
        stab_df = pd.concat(df_list)
        return pd.concat([test_seq_df, stab_df])
    else:
        return test_seq_df


def cut_off_intros(df):
    """Discards test set up and video countdown data at beginning of tests"""
    sdf = df.groupby(['tag']).first().loc[df['tag'].unique()].reset_index()
    sdf = sdf.dropna(subset=['test_time'])
    df_list = []
    for _, row in sdf.iterrows():
        # Isolate the test data for just this test
        tag = row['tag']
        single_test_df = df[df['tag'] == tag].copy()
        t = int(row['test_time'])
        end_time = max(single_test_df['time'])
        start_time = end_time - pd.Timedelta(seconds=t)
        single_test_df = single_test_df[single_test_df['time'] > start_time]
        single_test_df['seconds'] = range(len(single_test_df))
        df_list.append(single_test_df)

    return pd.concat(df_list)


def add_apl_data(df):
    """Merge APL data to main df."""
    apl_dfs = {clip_name: pd.read_csv(Path(sys.path[0]).joinpath(file)) for clip_name, file in APL_FILES.items()}
    df_list = []
    for clip_name, apl_df in apl_dfs.items():
        apl_df['video'] = clip_name
        df_list.append(apl_df)

    all_apl_df = pd.concat(df_list)
    df = df.merge(all_apl_df, on=['video', 'seconds'], how='left')
    df["APL'"] = df["APL'"].fillna(0)
    return df


def remove_rows_rewind(df, col='Tag'):

    start_tag_seq_df = df[df[col]!=df[col].shift(1)].dropna(subset=[col])
    duplicate_start = start_tag_seq_df[start_tag_seq_df[col].duplicated(keep='last')].index.values

    end_tag_seq_df = df[df[col]!=df[col].shift(-1)].dropna(subset=[col])
    duplicate_end = end_tag_seq_df[end_tag_seq_df[col].duplicated(keep='last')].index.values + 1

    remove_rows = []
    for start, end in zip(duplicate_start, duplicate_end):
        remove_rows += range(start, end)
    return df.drop(remove_rows)


def add_waketimes(merged_df, test_seq_df, data_df):
    """Calculate wake times from the test data and return as a dictionary."""
    waketimes = {}
    for _, row in test_seq_df.iterrows():
        if 'waketime' in row['test_name']:
            standby_tag = row['tag'] - 1
            standby_test = test_seq_df.query('tag==@standby_tag')['test_name'].iloc[0]
            wt_tag = f"{row['tag'] + .1} - user command"
            waketime = len(data_df.query('Tag==@wt_tag'))
            waketimes[standby_test] = waketime
            
    merged_df['waketime'] = merged_df['test_name'].apply(waketimes.get)
    return merged_df


def merge_test_data(test_seq_df, data_df):
    """
    Merges test output data, test sequence data, and APL data
    into a single cleaned csv ready to be used in data report script.
    """
    ddf = data_df.copy()
    ddf['Tag'] = ddf['Tag'].apply(lambda tag: tag[0] if 'camera ccf' in tag else tag)
    merged_df = remove_rows_rewind(ddf)
    merged_df['time'] = merged_df['Timestamp'].apply(round_time)
    merged_df = merged_df.drop_duplicates(subset=['time'])
    merged_df = merged_df.reset_index()[['time', 'Power', 'Luminance', 'Tag']]
    merged_df = merged_df.dropna(subset=['Tag'])
    merged_df['Tag'] = merged_df['Tag'].apply(clean_tag)
    merged_df = merged_df.dropna(subset=['Tag'])
    test_seq_df = add_stab_tests(test_seq_df, merged_df)
    merged_df.columns = ['time', 'watts', 'nits', 'tag']
    merged_df = merged_df.merge(test_seq_df, on='tag', how='left')
    merged_df = cut_off_intros(merged_df)
    merged_df = add_apl_data(merged_df)
    merged_df = add_waketimes(merged_df, test_seq_df, data_df)
    return merged_df

