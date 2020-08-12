import logging
from pathlib import Path

def cwd_logger(log_filename):
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    cwd_file_handler = logging.FileHandler(log_filename, mode='w')
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    cwd_file_handler.setFormatter(formatter)
    logger.addHandler(cwd_file_handler)
    
    return logger

def add_logfile(logger, filepath):
    df_file_handler = logging.FileHandler(filepath, mode='w')
    formatter = logging.Formatter(logging.BASIC_FORMAT)
    df_file_handler.setFormatter(formatter)
    logger.addHandler(df_file_handler)
