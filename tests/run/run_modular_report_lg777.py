import os
from pathlib import Path

def main():
    compliance_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\build\exe.win-amd64-3.6\compliance_report.exe'
    basic_report_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\build\exe.win-amd64-3.6\basic_report.exe'
    lum_report_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\build\exe.win-amd64-3.6\lum_report.exe'
    
    overlay_path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\build\exe.win-amd64-3.6\overlay.exe'
    
    lg77_estar_folder = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\SampleModels\LG777\ENERGYSTAR'
    os.system(f'{compliance_path} {lg77_estar_folder}')
    os.system(f'{basic_report_path} {lg77_estar_folder}')
    os.system(f'{lum_report_path} {lg77_estar_folder}')
    os.system(f'{overlay_path} {lg77_estar_folder} default brightest')
    
    
if __name__ == '__main__':
    main()