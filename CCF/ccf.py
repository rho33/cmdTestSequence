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
from scipy.optimize import minimize
from scipy.interpolate import CubicSpline
from docopt import docopt
sys.path.append('..')
from error_popups import permission_popup
import logfuncs as lf

@lf.log_output
def get_trendline(pps_df):
    # trendlines = {}
    # for col in ['r', 'g', 'b']:
    y = pps_df['photometer'].values
    x = pps_df['camera'].values

    def squared_percentage_error(w):
        slope, intercept = w
        y_pred = slope*x + intercept
        spe = ((y_pred - y)/y)**2
        return spe.sum()

    slope, intercept = minimize(squared_percentage_error, [1.0, 0.0]).x
    trendline = np.array([slope, intercept])
    return trendline


def get_spline(input_df):
    x = np.insert(input_df['signal'].values, 0, 0)
    y = np.insert(input_df['camera'].values, 0, 0).reshape(1, -1)
    y = normalize(y, norm='max').reshape(-1)

    return CubicSpline(x, y)


@lf.log_output
def get_w_outputs(rgb_dist_df, splines):
    outputs = {}
    for col in ['r', 'g', 'b']:
        cs = splines[col]
        output = rgb_dist_df[['signal', col]].apply(lambda row: cs(row['signal']) * row[col], axis=1).sum()
        outputs[col] = output
    w_outputs = {i: j / sum(outputs.values()) for i, j in outputs.items()}
    return w_outputs

@lf.log_output
def get_final_trendline(trendlines, w_outputs):
    weighted_trendlines = {color: trendline*w_outputs[color] for color, trendline in trendlines.items()}
    final_trendline = np.array(list(weighted_trendlines.values())).sum(axis=0)
    return final_trendline

@permission_popup
def main():
    logger = lf.cwd_logger('ccf.log')
    logger.info(str(sys.argv))
    docopt_args = docopt(__doc__)
    logger.info(docopt_args)
    
    if docopt_args['create']:
        path = docopt_args['<output_folder>']
        src = Path(sys.path[0]).joinpath('ccf-input-template.csv')
        dst = Path(path).joinpath('ccf-input.csv')
        if dst.exists():
            print(f'{dst} already exists')
        else:
            shutil.copy(src, dst)
            time.sleep(.5)
            # os.system(str(dst))
    else:
        drop_cols = ['photometer', 'camera']
        input_df = pd.read_csv(docopt_args['<input_path>']).dropna(subset=drop_cols, how='all')
        final_trendlines = {}
        for pps in input_df['pps'].unique():
            logger.info(f'\nPPS: {pps}')
            pps_df = input_df.query('pps==@pps')
            final_trendlines[pps] = get_trendline(pps_df)

        output_path = 'ccf-output.csv'
        if docopt_args['-o'] is not None:
            output_path = Path(docopt_args['-o']).joinpath(output_path)
        pd.DataFrame(data=final_trendlines, index=['slope', 'intercept']).T.to_csv(output_path)



if __name__ == '__main__':
    main()
