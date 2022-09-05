import os
import pandas as pd
import sys

def read_file(fname: str) -> pd.DataFrame:
    with open(fname, 'r') as infile:
        names = None
        value_table = []
        for line in infile:
            if line.startswith('Li'):
                line = line.strip().split()
                names, values = line[::2], line[1::2]
                values = list(map(float, values))
                value_table.append(values)
        names = [name.strip(':') for name in names]
        df = pd.DataFrame(value_table, columns=names)
        return df

def select_rows(df: pd.DataFrame, rcount: int = 5) -> pd.DataFrame:
    row_list = []
    added = set()
    for _, row in df.iterrows():
        liion, flywh, sucap = \
            map(int, row[['LiIon', 'Flywheel', 'Supercapacitor']])
        if (liion, flywh, sucap) not in added:
            added.add((liion, flywh, sucap))
            row_list.append(row)
        if len(row_list) > rcount: break
    return pd.DataFrame(row_list)

def row_to_string(row) -> str:
    outstr = ' | '.join(map(str, list(row)))
    outstr = '| ' + outstr + ' |'
    return outstr

def print_rows(rows: pd.DataFrame) -> None:
    head = row_to_string(rows.columns)
    print(head)
    print(row_to_string(['-'] * len(rows.columns)))
    for _, row in rows.iterrows():
        outstr = row_to_string(row)
        print(outstr)

def main():
    for fname in os.listdir():
        if fname.endswith('.log'):
            print('\n### ' + fname)
            df = read_file(fname)
            df = df.sort_values('Fitness', ascending=False)
            selected = select_rows(df)
            # print_rows(selected)
            selected.to_csv(sys.stdout, sep='\t')

if __name__ == '__main__':
    main()
