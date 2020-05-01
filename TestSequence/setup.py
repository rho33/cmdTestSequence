import sys
from shutil import copyfile
from cx_Freeze import setup, Executable
import os
from zipfile import ZipFile


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


# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"includes": ['pandas', 'docopt']}

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Console"

setup(  name = "TV Test Sequence",
        version = "0.1",
        description = 'Outputs test sequence and command sequence from cmd line input',
        options = {"build_exe": build_exe_options},
        executables = [Executable("tv_test_sequence.py", base=base)])

src = 'test-details.csv'
dst = 'build/exe.win-amd64-3.6/test-details.csv'
copyfile(src, dst)

zipdir('build/exe.win-amd64-3.6', './tv-test-sequence.zip')

