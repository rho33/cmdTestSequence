import sys
import logging
from functools import wraps
from pathlib import Path
from docopt import docopt

def cwd_logger(log_filename):
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    cwd_file_handler = logging.FileHandler(log_filename, mode='w')
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    cwd_file_handler.setFormatter(formatter)
    logger.addHandler(cwd_file_handler)
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
    logger = cwd_logger(log_filename)
    logger.info(sys.argv)
    docopt_args = docopt(doc)
    data_folder = Path(docopt_args.get('<data_folder>'))
    data_folder.mkdir(exist_ok=True)
    add_logfile(logger, data_folder.joinpath(log_filename))
    logger.info(sys.argv)
    logger.info(docopt_args)
    return logger, docopt_args, data_folder
    

