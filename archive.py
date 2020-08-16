import shutil
from datetime import datetime
from pathlib import Path

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