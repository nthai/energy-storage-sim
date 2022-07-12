import pandas as pd

def process_file(fname: str) -> pd.DataFrame:
    df = None
    if 'short.csv' in fname or 'full.csv' in fname:
        df = pd.read_csv(fname)
        df['timestamp'] = pd.to_datetime(df['timestamp'], format='%m%d%Y %H:%M')
        df['net'] = df['Load (kWh)'] - df['PV (kWh)']
    elif 'Sub71125' in fname:
        df = pd.read_csv(fname, sep=';', decimal=',')
        df['ReadTimestamp'] = pd.to_datetime(df['ReadTimestamp'])
        df['EntryDateTime'] = pd.to_datetime(df['EntryDateTime'])
        df = df.sort_values('ReadTimestamp', ascending=True).reset_index()
        df['net'] = df['Delta A+[kWh]']

        # TODO: find proper price data
        df['price (cents/kWh)'] = df['net'] # this is only temporary
    return df

def sum_above_below(pnets, lower, upper):
    sumbelow, sumabove = 0, 0
    for pnet in pnets:
        if pnet < lower:
            sumbelow += lower - pnet
        if pnet > upper:
            sumabove += pnet - upper
    return sumbelow, sumabove

def compute_limits(pnets):
    '''Compute an upper and lower limit for which the area below the lower limits and
    the area above the upper limit in the vector pnets is approximately the same.'''
    ordered = sorted(pnets)

    top, bot = ordered[-1], ordered[0]
    margin = (top - bot) / 6

    mid = (top + bot) / 2
    lowerlimit, upperlimit = mid - margin, mid + margin
    sumbelow, sumabove = sum_above_below(ordered, lowerlimit, upperlimit)
    
    while abs(sumabove - sumbelow) > 1e-10:
        if sumabove > sumbelow:
            bot = mid
        elif sumbelow > sumabove:
            top = mid
        else:
            break
        mid = (top + bot) / 2
        lowerlimit, upperlimit = mid - margin, mid + margin
        sumbelow, sumabove = sum_above_below(ordered, lowerlimit, upperlimit)

    return lowerlimit, upperlimit

def test_compute_limits():
    df = process_file('../data/Sub71125.csv')
    pnets = list(df['net'][1:25])
    print(pnets)

    lower, upper = compute_limits(pnets)
    print(lower, upper)

if __name__ == '__main__':
    test_compute_limits()
