import os
import sys
import PySimpleGUI as sg
from pathlib import Path
import time

prebuilt_choices = {
    'all_abc': 'all_abc standard dynamic --defabc --brabc --hdr standard --hdrabc',
    'no_abc': 'no_abc standard dynamic --hdr standard --qs 7'
}
layout = [
    [sg.DropDown(values=list(prebuilt_choices.keys()), key='prebuilt', size=(20, 5))],
    [sg.Text('TV Model')],
    [sg.InputText(key='model')],
    [sg.Text('Default PPS')],
    [sg.InputText(key='default_pps')],
    [sg.Checkbox('Default PPS ABC', key='--defabc')],
    [sg.Text('Brightest PPS')],
    [sg.InputText(key='brightest_pps')],
    [sg.Checkbox('Brightest PPS ABC', key='--brabc')],
    [sg.Text('HDR PPS')],
    [sg.InputText(key='hdr_pps')],
    [sg.Checkbox('HDR PPS ABC', key='--hdrabc')],
    [sg.Checkbox('QS On', key='qson')],
    [sg.Text('Wake Time (if qs off)')],
    [sg.Spin(list(range(1000)), initial_value=0, key='waketime')],
    [sg.Checkbox('use exe', key='exe')],
    [sg.Submit()],
]

window = sg.Window('Test Sequence Input').Layout(layout)
_, values = window.Read()
window.close()

if values['prebuilt']:
    args = prebuilt_choices[values['prebuilt']]
else:
    args = f"{values['model']} {values['default_pps']} {values['brightest_pps']}"
    if values['hdr_pps']:
        args += f" --hdr={values['hdr_pps']}"
    for option in ['--defabc', '--brabc', '--hdrabc']:
        if values[option]:
            args += f' {option}'
    if not values['qson']:
        args += f" --qs={values['waketime']}"
    
if values['exe']:
    path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\bin\build\exe.win-amd64-3.6\main_sequence.exe'
else:
    path = r'C:\Users\rhohe\PycharmProjects\cmdTestSequence\src\main_sequence.py'

# print(args)
os.system(f"{path} {args}")





# time.sleep(1)
# print('done sleeping 1')
# os.system(str(Path(sys.argv[1]).joinpath('test-sequence.csv')))
# print('dfdsa')
# time.sleep(3)
# print('done sleeping 2')
# os.system(str(Path(sys.argv[1]).joinpath('command-sequence.csv')))