import shutil
import os
from datetime import datetime
from pathlib import Path
from functools import partial
import warnings
from error_popups import permission_popup


@permission_popup
def send_file(filepath, dst_folder_name, copy=True, date=True):
    """Copy (or cut) a file and paste it in a destination sub-folder"""
    path = Path(filepath)
    dst_folder = path.parent.joinpath(dst_folder_name)
    if not dst_folder.exists():
        dst_folder.mkdir(parents=True)
    
    if date:
        today = datetime.today().strftime('%Y-%h-%d-%H-%M')
        save_path = dst_folder.joinpath(f'{path.stem}-{today}{path.suffix}')
    else:
        save_path = dst_folder.joinpath(f'{path.name}')
    
    if copy:
        shutil.copyfile(path, save_path)
    else:
        shutil.move(path, save_path)


archive = partial(send_file, dst_folder_name='Archive')

PATTERNS = {
    'test_seq': '*test-sequence*.csv',
    'test_data': '*datalog*.csv',
    'lum_profile': '*lum profile*.csv',
    'cmd_seq': '*command-sequence*.csv',
    'entry_forms': '*entry-forms*.xlsx',
    'repair_test_seq': 'Repair/*test-sequence*.csv',
    'repair_cmd_seq': 'Repair/*command-sequence*.csv',
    'repair_data': 'Repair/*datalog*.csv',
    'repair_lum_profile': 'Repair/*lum profile*.csv',
    'test_metadata': '*test-metadata*.csv'
}


def get_paths(data_folder):
    def get_path(pattern):
        path_list = list(Path(data_folder).glob(pattern))
        if path_list:
            most_recent = max(path_list, key=lambda x: os.path.getmtime(x))
            if len(path_list) > 1:
                path_list.remove(most_recent)
                for path in path_list:
                    archive(path, copy=False)
                warnings.warn(
                    f'''Multiple files found matching glob pattern {pattern} in {data_folder} .
                    The most recently modified file ({most_recent}) was used. The rest have been archived ({[path.stem for path in path_list]})'''
                             )
            return most_recent

    paths = {key: get_path(pattern) for key, pattern in PATTERNS.items()}
    return paths