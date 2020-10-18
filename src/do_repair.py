"""Usage:
do_repair.exe <data_folder>
"""
import sys
import shutil
from datetime import datetime
import warnings
import pandas as pd
sys.path.append('..')
import filefuncs as ff
import logfuncs as lf
from error_handling import permission_popup


def get_repair_df(path):
    df = pd.read_csv(path)
    mask = (df['Tag'].apply(lambda tag: 'repair' in tag)) & (df['Tag'].apply(lambda tag: 'user command' not in tag))
    repair_df = df[mask].copy()
    repair_df['Tag'] = repair_df['Tag'].apply(lambda tag: tag.replace('repair', '').strip())
    repair_df['source'] = str(path.stem)
    return repair_df


def check_contents(paths):

    msg = None
    if paths['test_data'] is None:
        msg = 'test data ("*datalog*.csv") file not found'
    elif paths['repair_data'] is None:
        msg = 'repair_data ("Repair/*datalog*.csv) file not found'
    
    if msg is not None:
        raise Exception(msg)


def stitch_repairs(data_df, repair_df):
    
    stitched_df = data_df.copy()
    for tag in repair_df['Tag'].unique():
        tdf = stitched_df[stitched_df['Tag']==tag]
        before_df = stitched_df.loc[:tdf.index[0]-1]
        repair_test_df = repair_df[repair_df['Tag']==tag]
        after_df = stitched_df.loc[tdf.index[-1]+1:]
        stitched_df = pd.concat([before_df, repair_test_df, after_df], sort=False)
        stitched_df.index = range(len(stitched_df))
    return stitched_df
    
@permission_popup
def save_stitched(stitched_df, data_df, paths):
    col_order = {col: i for i, col in enumerate(data_df.columns)}
    stitched_df.columns = sorted(stitched_df.columns, key=lambda col: col_order.get(col, len(col_order)+1))
    stitched_df.to_csv(paths['test_data'], index=False)
    
    
def main():
    logger, docopt_args, data_folder = lf.start_script(__doc__, 'do-repair.log')
    paths = ff.get_paths(data_folder)
    
    check_contents(paths)
    data_df = pd.read_csv(paths['test_data'])
    logger.info(f'data_df.describe()\n{data_df.describe().to_string()}')
    repair_df = get_repair_df(paths['repair_data'])
    logger.info(f'repair_df.describe():\n{repair_df.describe().to_string()}')
    stitched_df = stitch_repairs(data_df, repair_df)
    logger.info(f'stitched_df.describe():\n{stitched_df.describe().to_string()}')
    ff.archive(paths['test_data'], copy=False)
    
    if paths['repair_lum_profile'] is not None:
        ff.archive(paths['lum_profile'], copy=False)
        shutil.copyfile(paths['repair_lum_profile'], paths['lum_profile'])
        
    today = datetime.today().strftime('%Y-%h-%d-%H-%M')
    for path in ['repair_test_seq', 'repair_cmd_seq', 'repair_data', 'repair_lum_profile']:
        if paths[path] is None:
            if path != 'repair_lum_profile':
                warnings.warn(f'{ff.PATTERNS[path]} file not found')
        else:
            ff.send_file(paths[path], f'Completed/{today}', copy=False)
    
    save_stitched(stitched_df, data_df, paths)
    

    # todo: call report

if __name__ == '__main__':
    main()