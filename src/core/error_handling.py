from functools import partial, wraps
import PySimpleGUI as sg
import warnings
import logging

def error_popup(msg, callback, exception=Exception):
    p = sg.Popup(msg)
    if p is None:
        raise exception
    else:
        return callback()


def permission_popup(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PermissionError as e:
            msg = f'{e}\n\nClose the file referenced above and press OK to continue'
            error_popup(msg, partial(wrapper, *args, **kwargs), exception=e)
    return wrapper


def skip_and_warn(func):
    '''skips report section if exception is thrown and notifies user'''
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            warnings.filterwarnings('always', category=UserWarning)
            msg = f'\n{func.__name__} Failed:\n{e}'
            warnings.warn(msg)
            logging.exception(msg)
        return args[0]
    return wrapper


def except_none_log(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            msg = f'\n\n{func.__name__} Failed\n'
            logging.exception(msg)
            return None
    return wrapper