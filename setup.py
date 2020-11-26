import sys
from pathlib import Path
from cx_Freeze import setup, Executable
import os
from zipfile import ZipFile

sys.path.append(str(Path(sys.path[0]).joinpath('src')))

dst = Path(r'bin\build')
build_exe_options = {
    "packages": ['core'],
    "includes": ['pandas', 'docopt','matplotlib', 'matplotlib.backends.backend_tkagg', 'seaborn', 'scipy.ndimage._ni_support',
                 'seaborn.cm', 'scipy', 'scipy.spatial.ckdtree', 'scipy.sparse.csgraph._validation',
                 'multiprocessing.pool', 'mpl_toolkits', 'core'],
    "excludes": ['sqlite3', 'sklearn'],
    "include_files": [r'src\config', r'src\img'],
    "build_exe": str(dst),
    "include_msvcr": True,
    "replace_paths": [
        (r"C:\Users\rhohe\PycharmProjects\cmdTestSequence\venv", "<Python>"),
        (r"C:\Users\rhohe\PycharmProjects\cmdTestSequence\src", "<Scripts>"),
        (r"C:\Users\rhohe\PycharmProjects\cmdTestSequence\bin\build\lib", "<Scripts>")
    ],
}
install_exe_options = {'build_dir': str(dst)}
bdist_msi_options = {
    "initial_target_dir": r'C:\Program Files (x86)\DMC\TV Test System\External Scripts',
    "dist_dir": r'bin\dist',
    "bdist_dir": r'bin\dist\bdist'
}

base = None
if sys.platform == "win32":
    base = "Console"

setup(
    name = 'TV Test System Scripts',
    version = '0.13.0',
    description = "description",
    options = {
        "build_exe": build_exe_options,
        "install_exe": install_exe_options,
        "bdist_msi": bdist_msi_options
    },
    executables = [
        Executable(r"src\report.py", base=base),
        Executable(r"src\main_sequence.py", base=base),
        Executable(r"src\pcl_sequence.py", base=base),
        Executable(r"src\ccf.py", base=base),
        Executable(r"src\status.py", base=base),
    ]
)
# cx_freeze randomly capitalizes some folders/file names which then causes errors.
ckd = dst.joinpath(r'lib\scipy\spatial\cKDTree.cp36-win_amd64.pyd')
ckd.rename(ckd.parent.joinpath('ckdtree.cp36-win_amd64.pyd'))

pool = dst.joinpath(r'lib\multiprocessing\Pool.pyc')
pool.rename(pool.parent.joinpath('pool.pyc'))

tkinter = dst.joinpath(r'lib\Tkinter')
tkinter.rename(tkinter.parent.joinpath('tkinter'))

def zipdir(directory, destination=None):
    # path to folder which needs to be zipped

    # calling function to get all file paths in the directory
    file_paths = []

    # crawling through directory and subdirectories
    for root, directories, files in os.walk(directory):
        for filename in files:
            # join the two strings in order to form the full filepath.
            filepath = os.path.join(root, filename)
            file_paths.append(filepath)

    print('zipping...')
    # writing files to a zipfile
    if not destination:
        destination = f'{directory}.zip'
    with ZipFile(destination, 'w') as zip:
        # writing each file one by one
        for file in file_paths:
            zip.write(file)
    print('All files zipped successfully!')
zipdir(dst, str(dst.parent.joinpath('tv-test-scripts.zip')))