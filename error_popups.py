from functools import partial
import PySimpleGUI as sg


def error_popup(msg, callback, exception=Exception):
    p = sg.Popup(msg)
    if p is None:
        raise exception
    else:
        return callback()


def permission_popup(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PermissionError as e:
            msg = f'{e}\n\nClose the file referenced above and press OK to continue'
            error_popup(msg, partial(wrapper, *args, **kwargs), exception=e)
    
    return wrapper