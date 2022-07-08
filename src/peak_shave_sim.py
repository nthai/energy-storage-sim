import gym
import pandas as pd
from peak_shave_battery import PeakShaveEnergyHub

FILENAME = '../data/short.csv'
# FILENAME = '../data/full.csv'

class PeakShaveEnv(gym.Env):
    def __init__(self, config: dict) -> None:
        super().__init__()

        self.limdelta = config['delta_limit']
        self.upperlim = 3000
        self.lowerlim = 1000
        self.ehub = PeakShaveEnergyHub(config)

        if self.upperlim < self.lowerlim:
            raise Exception(f'Upper limit ({self.upperlim}) is lower than ' +
                            f'the lower limit ({self.lowerlim}!)')

        self.reset()

    def reset(self):
        '''Resets the state-of-charge in all batteries.'''
        self.ehub.reset()

    def set_limits(self, lower: float, upper: float):
        '''Set upper and lower limits for peak-shaving.'''
        self.upperlim = upper
        self.lowerlim = lower

    def get_available_actions(self) -> list[int]:
        '''Possible actions:
            - 0: do nothing
            - 1: dec. lower, dec. upper
            - 2: dec. lower, inc. upper
            - 3: inc. lower, dec. upper
            - 4: inc. lower, inc. upper
        '''

        availables = [1, 0, 0, 0, 1]

        if self.lowerlim - self.limdelta >= 0:
            availables[1] = 1
            availables[2] = 1
        
        if self.lowerlim + self.limdelta <= self.upperlim - self.limdelta:
            availables[3] = 1

        return availables

    def step(self, action: int, pnet: float, price: float):
        '''Makes a simulation step by charging/discharging the batteries based on the
        net power demand and calculates the cost paid for the energy taken from the
        grid.
        Args:
            - action: not implemented yet # TODO
            - pnet: net power demand for the next time period (in kW)
            - price: price of electricity in the next time period (in cents/kWh)
        Returns:
            - state: not implemented yet # TODO
            - reward: total cost in cents to pay to the grid (negative value)
            - done: end of episode (always False)
            - infos: extra info dictionary
        '''
        state = None
        reward = None
        done = False
        infos = []
        report = ''

        if __debug__:
            report += f'Demand: {pnet:8.2f} kW, '

        pbought = 0
        if pnet > self.upperlim:
            # the demand is higher than the upper limit, take energy from the battery
            pdischarge = pnet - self.upperlim
            total_discharge, total_selfdischarge = self.ehub.discharge(pdischarge)
            pbought = pnet - total_discharge

            if __debug__:
                report += (f'Purchased: {pbought:8.2f} kW, ')
                report += (f'Discharged: {total_discharge:6.2f} kW, ' +
                           f'SelfD: {total_selfdischarge:6.2f} kW ')
        elif pnet < self.lowerlim:
            # the demand is lower than the lower limit, use the excess to charge
            # the battery
            pcharge = self.lowerlim - pnet
            total_charge, total_selfdischarge = self.ehub.charge(pcharge)
            pbought = pnet + total_charge

            if __debug__:
                report += (f'Purchased: {pbought:8.2f} kW, ')
                report += (f'Charged:    {total_charge:6.2f} kW, ' +
                           f'SelfD: {total_selfdischarge:6.2f} kW ')
        else:
            # we do nothing, but there is still self-discharge!
            _, _, total_selfdischarge = self.ehub.do_nothing()
            pbought = pnet

            if __debug__:
                report += (f'Purchased: {pbought:8.2f} kW, ')
                report += (f'No charge/discharge,   ' +
                           f'SelfD: {total_selfdischarge:6.2f} kW ')

        cost = price * pbought / 100
        reward = -cost

        if __debug__:
            maxsoc = self.ehub.get_maxsoc()
            soc = self.ehub.get_soc()
            report += f'SOC: {soc:8.2f} kWh ({soc/maxsoc*100:6.2f}%) '
            report += f'Price: {price:7.2f} '
            report += f'Money spent: {cost:7.2f}'
            print(report)

        return state, reward, done, infos

class PeakShaveSim:
    def __init__(self, config, df=None):
        '''Creates a PeakShaveEnv environment for the simulation.
        Args:
            - config: dictionary containing the initializarion parameters
                - `filename`: name of the file containin the data. Necessary if no df
                    is provided through the constructor.
                - `delta_limit`: the amoun of power with which we can change the
                    upper or lower limit (in kW).
                - `LiIonBattery`: number of Li-Ion batteries.
                - `Flywheel`: number of flywheels.
                - `Supercapacitor`: number of supercapacitors.
            - df: pandas.DataFrame containing the net load and price data.
        '''
        self.env = PeakShaveEnv(config)
        self.df = self._read_df(config['filename']) if df is None else df

    def _read_df(self, fname: str) -> pd.DataFrame:
        df = pd.read_csv(fname)
        df['timestamp'] = pd.to_datetime(df['timestamp'],
                                         format='%m%d%Y %H:%M')
        df['net'] = df['Load (kWh)'] - df['PV (kWh)']
        return df

    def set_median_limits(self, margin=0.05):
        '''Sets the upper and lower limits around the median of the full dataset.
        Args:
            - margin: distance of the upper and lower limit from the median in %
        '''
        pmedian = self.df['net'].median()
        self.env.upperlim = pmedian * (1 + margin)
        self.env.lowerlim = pmedian * (1 - margin)
        if __debug__:
            print(f'Median net power: {pmedian}, ' +
                  f'Lower limit: {self.env.lowerlim}, ' + 
                  f'Upper limit: {self.env.upperlim}')

    def set_mean_limits(self, margin=0.05):
        '''Sets the upper and lower limits around the mean of the full dataset.
        Args:
            - margin: distance of the upper and lower limit from the mean in %
        '''
        pmean = self.df['net'].mean()
        self.env.upperlim = pmean * (1 + margin)
        self.env.lowerlim = pmean * (1 - margin)
        if __debug__:
            print(f'mean net power: {pmean}, ' +
                  f'Lower limit: {self.env.lowerlim}, ' + 
                  f'Upper limit: {self.env.upperlim}')

    def run_const_limits(self, lowerlim, upperlim):
        '''Runs the simulation with constant upper and lower limits.
        Args:
            - lowerlim: lower limit for the peak-shaving.
            - upperlim: upper limit for the peak-shaving.
        Returns:
            - total_costs: total cost accumulated during the simulation.
        '''
        total_costs = 0
        self.env.set_limits(lowerlim, upperlim)
        for _, datarow in self.df.iterrows():
            pnet = datarow['net']
            price = datarow['price (cents/kWh)']
            _, reward, _, _ = self.env.step(0, pnet, price)
            total_costs += -reward
        return total_costs
    
    def run_dynamic_limits(self, lookahead=4, margin=.05):
        '''Runs a simulation where the upper and lower limits for peak-shaving changes
        dynamically based on the median of future net power demand values.
        Args:
            - lookahead: the amount of future power values considered for the median.
            - margin: distance of upper and lower limits from the median.
        Returns:
            - total_costs: total cost accumulated during simulation.
        '''
        total_costs = 0
        for idx, datarow in self.df.iterrows():
            pmedian = self.df.iloc[idx:idx+lookahead]['net'].median()
            lowerlim = pmedian * (1 - margin)
            upperlim = pmedian * (1 + margin)
            self.env.set_limits(lowerlim, upperlim)

            pnet = datarow['net']
            price = datarow['price (cents/kWh)']
            _, reward, _, _ = self.env.step(0, pnet, price)
            total_costs += -reward

        return total_costs

def pkshave_constlims_objective(df: pd.DataFrame, liion_cnt: int, flywh_cnt: int,
                                sucap_cnt: int, margin: float) -> float:
    '''Objective for the peak-shave optimization problem. Upper and lower limits are
    set once at the start of the algorithm.
    Args:
        - df: pandas.DataFrame containing the price data and the net power under
            the 'net' key.
        - liion_cnt: number of LiIon batteries
        - flywh_cnt: number of flywheel batteries
        - sucap_cnt: number of supercapacitors
        - margin: determines the size of margin of the upper and lower limits from
          from the mean, i.e., (upperlim - mean) == (mean - lowerlim) == margin
    Returns:
        - total_costs: amount spent on buying electricity from the grid.
    '''
    mean_demand = df['net'].mean()
    upperlim = mean_demand * (1 + margin)
    lowerlim = mean_demand * (1 - margin)

    config = {
        'filename': FILENAME,
        'delta_limit': 1,
        'LiIonBattery': liion_cnt,
        'Flywheel': flywh_cnt,
        'Supercapacitor': sucap_cnt
    }
    sim = PeakShaveSim(config, df)
    total_costs = sim.run_const_limits(lowerlim, upperlim)
    return total_costs

def pkshave_dinlims_objective(df: pd.DataFrame, liion_cnt: int, flywh_cnt: int,
                              sucap_cnt: int, lookahead: int, margin: float) -> float:
    '''Objective for the peak-shave optimization problem. Upper and lower limits
    change dynamically during the run.
    Args:
        - df: pandas.DataFrame containing the price data and the net power data
            under the `net` key.
        - liion_cnt: number of LiIon batteries
        - flywh_cnt: number of flywheel batteries
        - sucap_cnt: number of supercapacitors
        - lookahead: number of future values to consider for the median
        - margin: determines the size of margin of the upper and lower limits from
          from the mean, i.e., (upperlim - mean) == (mean - lowerlim) == margin
    Returns:
        - total_costs: amount spent on buying electricity from the grid.
    '''
    config = {
        'filename': FILENAME,
        'delta_limit': 1,
        'LiIonBattery': liion_cnt,
        'Flywheel': flywh_cnt,
        'Supercapacitor': sucap_cnt
    }
    sim = PeakShaveSim(config, df)
    total_costs = sim.run_dynamic_limits(lookahead, margin)
    return total_costs

def main():
    df = pd.read_csv(FILENAME)
    df['timestamp'] = pd.to_datetime(df['timestamp'],
                                     format='%m%d%Y %H:%M')
    df['net'] = df['Load (kWh)'] - df['PV (kWh)']
    total_costs = pkshave_constlims_objective(df, 3, 3, 3, .2)
    print(total_costs)

if __name__ == '__main__':
    main()
