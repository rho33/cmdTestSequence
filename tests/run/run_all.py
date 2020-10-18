"""Usage:
run_all.py <data_folder> [options]

Options:
  -h --help
  --exe
  --estar
  --pcl
  --alt

"""
import os
import sys
import subprocess
from pathlib import Path
from docopt import docopt


def run_sequence(seq_type, data_subfolder, script_dir, exe=False):
    ext = '.exe' if exe else '.py'

    seq_scripts = {
        'estar': fr'{script_dir}\main_sequence{ext} {data_subfolder} aps vivid --hdr standard --qs 7',
        'pcl': fr'{script_dir}\pcl_sequence{ext} {data_subfolder}',
        'alternative': fr'{script_dir}\main_sequence{ext} {data_subfolder} aps vivid --hdr standard --defabc --brabc --hdrabc --qs 7'
    }
    print(f'running {seq_type} sequence')
    subprocess.run(seq_scripts[seq_type], shell=True)


def get_seq_types(docopt_args):
    seq_types = []
    if docopt_args['--estar']:
        seq_types.append('estar')
    if docopt_args['--alt']:
        seq_types.append('alternative')
    if docopt_args['--pcl']:
        seq_types.append['pcl']
    if not seq_types:
        seq_types = ['estar', 'alternative', 'pcl']
    return seq_types


def mock_data(data_subfolder):
    mock_cmd = fr"{sys.path[0]}\..\Mock\mock_data.py {data_subfolder}"
    print(f'mocking {data_subfolder}')
    subprocess.run(mock_cmd, shell=True)
    

def run_reports(script_dir, data_subfolder, exe=False):
    ext = '.exe' if exe else '.py'
    
    for script in ['report', 'basic_report', 'apl_power_charts', 'lum_report']:
        cmd = fr'{script_dir}\{script}{ext} {data_subfolder}'
        print(f'running {script}{ext}')
        subprocess.run(cmd, shell=True)


def main():
    docopt_args = docopt(__doc__)
    script_dir = fr'{sys.path[0]}\..\..\bin\build' if docopt_args['--exe'] else fr'{sys.path[0]}\..\..\src'
    script_dir = Path(script_dir)
    seq_types = get_seq_types(docopt_args)
    
    for seq_type in seq_types:
        data_subfolder = {'estar': 'ENERGYSTAR', 'alternative': 'Alternative', 'pcl': 'PCL'}[seq_type]
        data_subfolder = Path(docopt_args['<data_folder>']).joinpath(data_subfolder)
        data_subfolder.mkdir(exist_ok=True, parents=True)
        run_sequence(seq_type=seq_type, data_subfolder=data_subfolder, script_dir=script_dir, exe=docopt_args['--exe'])
        mock_data(data_subfolder)
        run_reports(script_dir, data_subfolder, exe=docopt_args['--exe'])
        

if __name__ == '__main__':
    main()
    
    

# os.chdir(r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\SampleModels')
# model = 'LG777'
#
# exe = False
# if exe:
#     main_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\build\exe.win-amd64-3.6\main_sequence.exe'
#     pcl_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\build\exe.win-amd64-3.6\pcl_sequence.exe'
#     repair_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\build\exe.win-amd64-3.6\repair_sequence.exe'
# else:
#     main_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\TestSequence\main_sequence.py'
#     pcl_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\TestSequence\pcl_sequence.py'
#     repair_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\TestSequence\repair_sequence.py'
# do_repair_path = r"C:\Users\rhohe\PycharmProjects\cmdTestSequence\do_repair.py"
# mock_path = r"C:\Users\rhohe\PycharmProjects\cmdTestSequence\Mock\mock_data.py"
# manual_path = r"C:\Users\rhohe\PycharmProjects\cmdTestSequence\TestSequence\manual_sequence.py"
#
# manual_data_folder = Path(model).joinpath('Manual')
# manual_data_folder.mkdir(exist_ok=True, parents=True)
# print('running Manual...')
# os.system(f"{manual_path} {manual_data_folder}")
#
# estar_data_folder = Path(model).joinpath('ENERGYSTAR')
# estar_data_folder.mkdir(exist_ok=True, parents=True)
# print('running ENERGYSTAR...')
# os.system(f"{main_path} {estar_data_folder} aps vivid --hdr standard --qs 7")
# print('mocking ENERGYSTAR...')
# os.system(f"{mock_path} {estar_data_folder}")
#
# print('running ENERGYSTAR repair sequence...')
# os.system(f"{repair_path} {estar_data_folder} 10 16")
# print('mocking ENERGYSTAR Repair...')
# os.system(f"{mock_path} {estar_data_folder.joinpath('Repair')}")
# print('running ENERGYSTAR do_repair...')
# os.system(f"{do_repair_path} {estar_data_folder}")
#
#
# alternative_data_folder = Path(model).joinpath('Alternative')
# alternative_data_folder.mkdir(exist_ok=True, parents=True)
# print('running Alternative...')
# os.system(f"{main_path} {alternative_data_folder} aps vivid --hdr standard --defabc --brabc --hdrabc --qs 7")
# print('mocking Alternative...')
# os.system(f"{mock_path} {alternative_data_folder}")
#
# print('running Alternative repair sequence...')
# os.system(f"{repair_path} {alternative_data_folder} 10 16")
# print('mocking Alternative Repair...')
# os.system(f"{mock_path} {alternative_data_folder.joinpath('Repair')}")
# print('running Alternative do_repair')
# os.system(f"{do_repair_path} {alternative_data_folder}")
#
#
# pcl_data_folder = Path(model).joinpath('PCL')
# pcl_data_folder.mkdir(exist_ok=True, parents=True)
# print('running PCL...')
# os.system(f"{pcl_path} {pcl_data_folder}")
# print('mocking PCL...')
# os.system(f"{mock_path} {pcl_data_folder}")
#
# print('running PCL repair sequence...')
# os.system(f"{repair_path} {pcl_data_folder} 10 16")
# print('mocking PCL Repair...')
# os.system(f"{mock_path} {pcl_data_folder.joinpath('Repair')}")
# print('running PCL do_repair')
# os.system(f"{do_repair_path} {pcl_data_folder}")
#
#
# def run_sequence():
#     print('running {var}')
    
    

    