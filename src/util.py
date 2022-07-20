import math
from datetime import datetime
import pandas as pd

class FluctuationCalculator:
    '''Class object computes and stores the net power fluctuation.'''
    def __init__(self) -> None:
        self.prev_value = None
        self.count = 0
        self.total = 0
        self.diff_total = 0

    def store(self, value) -> None:
        '''Computes the difference between two consecutive `power` values;
        aggregates the value into a sum and increases the count of values
        by 1.
        Args:
            - value: the power value to store.'''
        if self.prev_value is not None:
            diff = abs(self.prev_value - value)
            self.diff_total += diff
        self.total += value
        self.count += 1
        self.prev_value = value

    def get_net_demand_fluctuation(self) -> float:
        return self.diff_total / (self.total / self.count)

class FluctuationPeriodCalculator:
    '''Computes the mean net power fluctuation, by computing the power
    fluctuation for every 24 hours and storing it in a list. The mean
    of such fluctuations give the mean power fluctuation.'''
    def __init__(self) -> None:
        self.prev_value = None
        self.diff_total = 0
        self.total = 0
        self.count = 0

        self.fluct_list = []

    def store(self, timestamp: datetime, value: float) -> float:
        if self.prev_value is not None:
            diff = abs(self.prev_value - value)
            self.diff_total += diff

        self.total += value
        self.count += 1            
        self.prev_value = value

        if timestamp.hour == 23:
            fluctuation = self.diff_total / (self.total / self.count)
            self.fluct_list.append(fluctuation)
            self.diff_total = 0
            self.total = 0
            self.count = 0
            self.prev_value = None
        
    def get_mean_net_demand_fluctuation(self) -> float:
        return sum(self.fluct_list) / len(self.fluct_list)

class PeakPowerSumCalculator:
    '''Detects whether power value is a local peak and stores it if
    it is above the upper threshold limit.'''
    def __init__(self, df: pd.DataFrame) -> None:
        '''Args:
            - df: pandas.DataFrame of the input file. `net` must be key of
                net power demand.'''
        self.df = df
        self.peaks = []

    def _is_peak(self, idx, delta) -> bool:
        '''Checks whether df.iloc[idx] is larger than df.iloc[idx-1] and
        df.iloc[idx+1] and also checks if df.iloc[idx] is maximum in
        df.iloc[idx-delta:idx+delta].'''
        curr_value = self.df.iloc[idx]['net']
        if idx > 0 and self.df.iloc[idx - 1]['net'] > curr_value:
            return False
        if idx < len(self.df) - 1 and self.df.iloc[idx + 1]['net'] > curr_value:
            return False


        left = max(idx - delta, 0)
        right = min(len(self.df) - 1, idx + delta)
        if any(math.isclose(self.df.iloc[idx]['net'], self.df.iloc[i]['net'])
               for i in range(left, right + 1) if i != idx):
            return False
        local_peak = max(self.df.iloc[left:right]['net'])
        return math.isclose(curr_value, local_peak)

    def store(self, idx: int, upperlim, delta: int=10):
        '''Checks if data point at idx is a local peak in the pandas dataframe.
        Args:
            - idx: the index/location of the datapoint in the dataframe in question.
            - upperlim: the limit above which we consider a peak. If df.iloc[idx] id below
                upperlim, we ignore the data point.
            - delta: datapoint is peak if it is larger than adjacent values and is maximum
                in the [idx - delta, ..., idx + delta] range.
        '''
        curr_value = self.df.iloc[idx]['net']
        if curr_value > upperlim and self._is_peak(idx, delta):
            self.peaks.append(curr_value)

    def get_peak_power_sum(self) -> float:
        return sum(self.peaks)
    
    def get_peak_count(self) -> int:
        return len(self.peaks)

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

def compute_limits(pnets, tolerance=2):
    '''Compute an upper and lower limit for which the area below the lower limits and
    the area above the upper limit in the vector pnets is approximately the same.
    Args:
        - pnets: list of power demands for the next period (e.g. 24 hours) in kW.
        - tolerance: algorithms runs until the difference between the sum above the
              upper limit and the sum below the lower limit reaches the tolerance
              value (in kW)
    Returns:
        - lowerlimit: limit for the lower threshold (in kW)
        - upperlimit: limit for the upper threshold (in kW)'''
    ordered = sorted(pnets)

    top, bot = ordered[-1], ordered[0]
    margin = (top - bot) / 6

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

    return lowerlimit, upperlimit

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
            df = pd.DataFrame({'x': x, 'net': y})
            ppscalc = PeakPowerSumCalculator(df)

            for idx, _ in df.iterrows():
                ppscalc.store(idx, 1, 10)
            
            self.assertEqual(ppscalc.get_peak_count(), 2)

        def test2(self):
            x = np.arange(0, 10, 0.01)
            y = np.sin(x) + 1
            df = pd.DataFrame({'x': x, 'net': y})
            ppscalc = PeakPowerSumCalculator(df)

            for idx, _ in df.iterrows():
                ppscalc.store(idx, 2, 10)
            
            self.assertEqual(ppscalc.get_peak_count(), 0)
        
        def test3(self):
            x = np.arange(0, 10, 0.01)
            df = pd.DataFrame({'net': x})
            ppscalc = PeakPowerSumCalculator(df)
            for idx, _ in df.iterrows():
                ppscalc.store(idx, 0, 10)
            self.assertEqual(ppscalc.get_peak_count(), 0)

        def test4(self):
            x = np.arange(0, -10, -0.01)
            df = pd.DataFrame({'net': x})
            ppscalc = PeakPowerSumCalculator(df)
            for idx, _ in df.iterrows():
                ppscalc.store(idx, 0, 10)
            self.assertEqual(ppscalc.get_peak_count(), 0)
            self.assertEqual(ppscalc.get_peak_count(), 0)

        def test5(self):
            x = [1 if i%2 == 0 else -1 for i in range(100)]
            df = pd.DataFrame({'net': x})
            ppscalc = PeakPowerSumCalculator(df)
            for idx, _ in df.iterrows():
                ppscalc.store(idx, 0, 10)
            self.assertEqual(ppscalc.get_peak_count(), 0)

    class TestFluctuationCalculator(unittest.TestCase):
        def test1(self):
            fcalc = FluctuationCalculator()
            count = 100
            rndlist = np.random.rand(count)
            num, den = 0, 0
            for i in range(count):
                if i > 0:
                    num += abs(rndlist[i] - rndlist[i - 1])
                den += rndlist[i]
                fcalc.store(rndlist[i])
            den /= count
            fluct = num / den

            self.assertAlmostEqual(fluct, fcalc.get_net_demand_fluctuation())

        def test2(self):
            nums = [1.23] * 50
            fcalc = FluctuationCalculator()
            for elem in nums:
                fcalc.store(elem)
            self.assertAlmostEqual(fcalc.get_net_demand_fluctuation(), 0)

    unittest.main()

def chop(val, to=0, delta=1e-10):
    if to - delta <= val <= to + delta:
        return to
    else:
        return val