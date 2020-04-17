import sys
from shutil import copyfile
from cx_Freeze import setup, Executable


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