"""Usage:
ccf.exe <input_path> [options]
ccf.exe create <output_folder>

Options:
  -h --help
  -o=path    output folder path
"""
import sys
import os
import shutil
import time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize
from scipy.stats import linregress
from scipy.interpolate import CubicSpline
from docopt import docopt


def get_rgb_trendlines(photometer_df, camera_df):
    trendlines = {}
    for col in ['r', 'g', 'b']:
        x = photometer_df[col]
        y = camera_df[col]
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        trendlines[col] = np.array([slope, intercept])
    return trendlines


def get_splines(camera_df):
    x = np.insert(camera_df['signal'].values, 0, 0)
    signal = camera_df['signal'].values
    splines = {}
    for col in ['r', 'g', 'b']:
        y = np.insert(camera_df[col].values, 0, 0).reshape(1, -1)
        y = normalize(y, norm='max').reshape(-1)
        splines[col] = CubicSpline(x, y)
    return splines


def get_final_trendline(rgb_dist_df, trendlines, splines):
    outputs = {}
    for col in ['r', 'g', 'b']:
        cs = splines[col]
        output = rgb_dist_df[['signal', col]].apply(lambda row: cs(row['signal']) * row[col], axis=1).sum()
        outputs[col] = output

    w_outputs = {i: j/sum(outputs.values()) for i, j in outputs.items()}
    weighted_trendlines = {color: trendline*w_outputs[color] for color, trendline in trendlines.items()}

    final_trendline = np.array(list(weighted_trendlines.values())).sum(axis=0)

    return final_trendline


def main():
    docopt_args = docopt(__doc__)
    if docopt_args['create']:
        path = docopt_args['<output_folder>']
        src = Path(sys.path[0]).joinpath('ccf-input-template.csv')
        dst = Path(path).joinpath('ccf-input.csv')
        if dst.exists():
            print(f'{dst} already exists')
        else:
            shutil.copy(src, dst)
            time.sleep(.5)
            os.system(str(dst))
    else:
        
        drop_cols = ['r_photometer', 'g_photometer', 'b_photometer', 'r_camera', 'g_camera', 'b_camera']
        input_df = pd.read_csv(docopt_args['<input_path>']).dropna(subset=drop_cols, how='all')
        final_trendlines = {}
        for pps in input_df['pps'].unique():
            pps_df = input_df.query('pps==@pps')
            
            photometer_df = pps_df[['signal', 'r_photometer', 'g_photometer', 'b_photometer']].copy()
            photometer_df.columns = ['signal', 'r', 'g', 'b']
            camera_df = pps_df[['signal', 'r_camera', 'g_camera', 'b_camera']].copy()
            camera_df.columns = ['signal', 'r', 'g', 'b']
            
            if pps == 'hdr_default':
                rgb_dist_df = pd.read_csv(Path(sys.path[0]).joinpath('rgb_distribution_hdr.csv'))
            else:
                rgb_dist_df = pd.read_csv(Path(sys.path[0]).joinpath('rgb_distribution_sdr.csv'))
            
            trendlines = get_rgb_trendlines(photometer_df, camera_df)
            splines = get_splines(camera_df)
            final_trendlines[pps] = get_final_trendline(rgb_dist_df, trendlines, splines)
        
        output_path = 'ccf-output.csv'
        if docopt_args['-o'] is not None:
            output_path = Path(docopt_args['-o']).joinpath(output_path)
        pd.DataFrame(data=final_trendlines, index=['slope', 'intercept']).T.to_csv(output_path)
        time.sleep(.5)
        os.system(str(output_path))


if __name__ == '__main__':
    main()
