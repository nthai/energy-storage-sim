import math
from datetime import datetime
import pandas as pd

def calc_fluctuation(powers: list):
    '''Calculates fluctuation of power.
    Args:
        - powers: list of tuples containin the following values: (`timestamp`, `pnet`,
            `pbought`, `soc`, `upper`[optional], `lower`[optional])
    Returns: the fluctuation value.'''
    size = len(powers)
    total_diff = 0
    for idx in range(1, size):
        diff = abs(powers[idx][2] - powers[idx - 1][2])
        total_diff += diff
    psum = sum([power[2] for power in powers])
    mean = psum / size
    return total_diff / mean

def calc_periodic_fluctuation(powers: list):
    '''Calculates the periodic fluctuation of power with a 24 hour period
    Args:
        - powers: list of tuples containin the following values: (`timestamp`, `pnet`,
            `pbought`, `soc`, `upper`[optional], `lower`[optional])
    Returns: the fluctuation value.'''

    prev_p = None
    total_diff = 0
    psum = 0
    count = 0
    fluct_sum = 0
    fluct_cnt = 0
    for power in powers:
        psum += power[2]
        count += 1
        if prev_p is None:
            prev_p = power[2]
        else:
            diff = abs(power[2] - prev_p)
            total_diff += diff
            prev_p = power[2]
        if power[0].hour == 23:
            fluct = 0
            if psum != 0 and count != 0:
                fluct = total_diff / (psum / count)
            fluct_sum += fluct
            fluct_cnt += 1
            prev_p = None
            total_diff, psum, count = 0, 0, 0
    return fluct_sum / fluct_cnt

def is_peak(powers: list, idx: int, delta: int) -> bool:
    curr_value = powers[idx][2]
    if idx > 0 and powers[idx - 1][2] >= curr_value:
        return False
    if idx < len(powers) - 1 and powers[idx - 1][2] >= curr_value:
        return False
    if idx == 0 or idx == len(powers) - 1:
        return False
    
    left = max(idx - delta, 0)
    right = min(len(powers), idx + delta + 1)
    if any(math.isclose(curr_value, powers[i][2]) for i in range(left, right)
           if i != idx):
        return False
    local_peak = max(powers[i][2] for i in range(left, right))
    return math.isclose(curr_value, local_peak)

def calc_peak_power_sum(powers: list):
    '''Calculates sum of peaks above the upper limit.
    Args:
        - powers: list of tuples containin the following values: (`timestamp`, `pnet`,
            `pbought`, `soc`, `lower`, `upper`)
    Returns:
        - the sum of peaks,
        - the number of peaks.'''

    total = 0
    count = 0
    for idx, power in enumerate(powers):
        if is_peak(powers, idx, 10) and power[2] > power[5]:
            count += 1
            total += power[2] - power[5]
    return total, count

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
        df['timestamp'] = df['ReadTimestamp']
        # TODO: find proper price data
        df['price (cents/kWh)'] = df['net'] # this is only temporary
    return df

def sum_above_below(pnets, lower, upper):
    '''Calculates the sum of values in the pnets list above the upper limit
    and below the lower limit.
    Args:
        - pnets: list of net power demand values
        - lower: lower limit
        - upper: upper limit
    Returns:
        - sumbelow: total area below the lower limit
        - sumabove: total area above the upper limit'''
    sumbelow, sumabove = 0, 0
    for pnet in pnets:
        if pnet < lower:
            sumbelow += lower - pnet
        if pnet > upper:
            sumabove += pnet - upper
    return sumbelow, sumabove

def compute_limits(pnets, tolerance=2, margin=0.25, factor=1):
    '''Compute an upper and lower limit for which the area below the lower limits and
    the area above the upper limit in the vector pnets is approximately the same.
    Args:
        - pnets: list of power demands for the next period (e.g. 24 hours) in kW.
        - tolerance: algorithms runs until the difference between the sum above the
            upper limit and the sum below the lower limit reaches the tolerance
            value (in kW)
        - margin: sets the the distance of the upper and the lower limit from the mid
            point. Its value is the percentage of the distance between the max and the
            min value of pnets.
        - factor: lowerlimit is multiplied by factor at the end. TODO: experiment with
            factor > 1 to see if having a higher lowerlimit give us a more efficient
            operation.
    Returns:
        - lowerlimit: limit for the lower threshold (in kW)
        - upperlimit: limit for the upper threshold (in kW)'''
    ordered = sorted(pnets)

    top, bot = ordered[-1], ordered[0]
    margin = (top - bot) * margin

    mid = (top + bot) / 2
    lowerlimit, upperlimit = mid - margin, mid + margin
    sumbelow, sumabove = sum_above_below(ordered, lowerlimit, upperlimit)

    while abs(sumabove - sumbelow) > tolerance:
        if sumabove > sumbelow:
            bot = mid
        elif sumbelow > sumabove:
            top = mid
        else:
            break
        mid = (top + bot) / 2
        lowerlimit, upperlimit = mid - margin, mid + margin
        sumbelow, sumabove = sum_above_below(ordered, lowerlimit, upperlimit)

    return lowerlimit * factor, upperlimit

def test_compute_limits():
    df = process_file('../data/Sub71125.csv')
    pnets = list(df['net'][1:25])
    print(pnets)

    lower, upper = compute_limits(pnets)
    print(lower, upper)

if __name__ == '__main__':
    # test_compute_limits()
    
    import unittest
    import numpy as np
    import matplotlib.pyplot as plt

    class TestPeakPowerSumCalculator(unittest.TestCase):
        def test1(self):
            x = np.arange(0, 10, 0.01)
            y = np.sin(x) + 1

            c = np.array([1] * x.size)
            powers = np.array([x, y, y, c, c, c]).transpose()
            _, count = calc_peak_power_sum(powers)

            self.assertEqual(count, 2)

        def test2(self):
            x = np.arange(0, 10, 0.01)
            y = np.sin(x) + 1
            
            c = np.array([2] * x.size)
            powers = np.array([x, y, y, c, c, c]).transpose()
            _, count = calc_peak_power_sum(powers)
            
            self.assertEqual(count, 0)
        
        def test3(self):
            x = np.arange(0, 10, 0.01)

            c = np.array([1] * x.size)
            powers = np.array([x, x, x, c, c, c]).transpose()
            _, count = calc_peak_power_sum(powers)
            
            self.assertEqual(count, 0)

        def test4(self):
            x = np.arange(0, -10, -0.01)

            c = np.array([1] * x.size)
            powers = np.array([x, x, x, c, c, c]).transpose()
            _, count = calc_peak_power_sum(powers)

            self.assertEqual(count, 0)

        def test5(self):
            x = [1 if i%2 == 0 else -1 for i in range(100)]
            
            c = np.array([1] * 100)
            powers = np.array([x, x, x, c, c, c]).transpose()
            _, count = calc_peak_power_sum(powers)
            
            self.assertEqual(count, 0)

    class TestFluctuationCalculator(unittest.TestCase):
        def test1(self):
            count = 100
            rndlist = np.random.rand(count)
            powers = np.array([rndlist, rndlist, rndlist]).transpose()
            num, den = 0, 0
            for i in range(count):
                if i > 0:
                    num += abs(rndlist[i] - rndlist[i - 1])
                den += rndlist[i]

            fcalc = calc_fluctuation(powers)
            den /= count
            fluct = num / den

            self.assertAlmostEqual(fluct, fcalc)

        def test2(self):
            nums = [1.23] * 50
            powers = np.array([nums, nums, nums]).transpose()
            fcalc = calc_fluctuation(powers)
            self.assertAlmostEqual(fcalc, 0)

    unittest.main()

def chop(val, to=0, delta=1e-10):
    if to - delta <= val <= to + delta:
        return to
    else:
        return val