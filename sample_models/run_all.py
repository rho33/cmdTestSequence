"""Generates TV test sequences, mocks data based on TV test sequence, and runs report scripts on mocked data
Usage:
run_all.py <data_folder> [options]

Options:
  -h --help
  --exe=path   use frozen scripts, path to frozen scripts
  --estar      include ENERGYSTAR test sequence
  --pcl        include PCL test sequence
  --alt        include alternative test sequence
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
    mock_cmd = fr"{sys.path[0]}\mock\mock_data.py {data_subfolder}"
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
    if docopt_args['--exe'] is not None:
        script_dir = docopt_args['--exe']
    else:
        script_dir = fr'{sys.path[0]}\..\src'
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