import shutil
from datetime import datetime
from pathlib import Path
from functools import partial
from error_popups import permission_popup

def archive(filepath, copy=True, date=False):
    """Copy (or cut) a file and paste it in the Archive sub-folder"""
    path = Path(filepath)
    archive_dir = path.parent.joinpath('Archive')
    if not archive_dir.exists():
        archive_dir.mkdir()

    if date:
        today = datetime.today().strftime('%Y-%h-%d-%H-%M')
        save_path = archive_dir.joinpath(f'{path.stem}-{today}{path.suffix}')
    else:
        save_path = archive_dir.joinpath(f'{path.name}')

    if copy:
        shutil.copyfile(path, save_path)
    else:
        shutil.move(path, save_path)
        
@permission_popup
def send_file(filepath, dst_folder_name, copy=True, date=True):
    """Copy (or cut) a file and paste it in a destination sub-folder"""
    path = Path(filepath)
    dst_folder = path.parent.joinpath(dst_folder_name)
    if not dst_folder.exists():
        dst_folder.mkdir()
    
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
    'entry-forms': '*entry-forms*.xlsx',
    'repair_test_seq': 'Repair/*test-sequence*.csv',
    'repair_cmd_seq': 'Repair/*command-sequence*.csv',
    'repair_data': 'Repair/*datalog*.csv',
    'repair_lum_profile': 'Repair/*lum profile*.csv'
}

def get_paths(data_folder):
    def get_path(pattern):
        path_list = list(data_folder.glob(pattern))
        if path_list:
            return path_list[0]

    paths = {key: get_path(pattern) for key, pattern in PATTERNS.items()}
    return paths