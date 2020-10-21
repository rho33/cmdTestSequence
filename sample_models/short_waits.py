"""Usage:
short_waits.py command_sequence_path
"""
import sys
import pandas as pd

def main():
    path = sys.argv[1]
    cdf = pd.read_csv(path, header=None)
    cdf.loc[cdf[0]=='wait', 1] = 5
    cdf.loc[cdf[2].notnull(), 2] = 30
    cdf.loc[cdf[3].notnull(), 3] = 2
    cdf.to_csv(path, index=False, header=False)
    
if __name__ == '__main__':
    main()
