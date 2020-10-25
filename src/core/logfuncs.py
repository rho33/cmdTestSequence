import sys
import logging
from functools import wraps
from pathlib import Path
from docopt import docopt
from .filefuncs import APPDATA_DIR


def appdata_logger(log_filename):

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    appdata_file_handler = logging.FileHandler(str(APPDATA_DIR.joinpath(log_filename)), mode='w')
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    appdata_file_handler.setFormatter(formatter)
    logger.addHandler(appdata_file_handler)
    return logger

def log_output(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        output = func(*args, **kwargs)
        logging.info(f'{func.__name__}: {output}')
        return output
    return wrapper
    
    
def add_logfile(logger, filepath):
    df_file_handler = logging.FileHandler(filepath, mode='w')
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    df_file_handler.setFormatter(formatter)
    logger.addHandler(df_file_handler)
    
    
def start_script(doc, log_filename):
    logger = appdata_logger(log_filename)
    logger.info(sys.argv)
    docopt_args = docopt(doc)
    data_folder = docopt_args.get('<data_folder>')
    if data_folder is not None:
        data_folder = Path(docopt_args.get('<data_folder>'))
        data_folder.mkdir(exist_ok=True)
        add_logfile(logger, data_folder.joinpath(log_filename))
        
    logger.info(sys.argv)
    logger.info(docopt_args)
    return logger, docopt_args, data_folder
    

