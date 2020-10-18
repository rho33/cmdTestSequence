import os
import sys

data_folder = sys.argv[1]
exe_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\build\exe.win-amd64-3.6\report.exe'
os.system(f'{exe_path} {data_folder}')
os.chdir(data_folder)
os.system('report.pdf')