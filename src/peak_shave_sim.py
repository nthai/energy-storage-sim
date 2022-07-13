import argparse
import gym
import pandas as pd
from peak_shave_battery import PeakShaveEnergyHub
from util import process_file
from util import compute_limits

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
        '''Returns a list containing 0s and 1s. The i-th element of the list
        tells whether action i is executable. The value i//3 determines the
        action we execute on the upper limit, and the value i%3 determines
        the action we execute on the lower limit. 0 means do nothing, 1 means
        decrease, 2 means increase.
        '''

        availables = [1, 0, 0, 0, 0, 0, 1, 0, 1]

        if self.lowerlim - self.limdelta >= 0:
            # we can decrease the lower limit
            availables[1] = 1
            availables[4] = 1
            availables[7] = 1
        
        if self.lowerlim + self.limdelta <= self.upperlim - self.limdelta:
            # we can increase the lower limit while decreasing the upper limit
            availables[5] = 1
        
        if self.upperlim - self.lowerlim >= self.limdelta:
            # we can increase the lower limit or decrease the upper limit
            availables[2] = 1
            availables[3] = 1

        return availables

    def _execute_action(self, action: int):
        assert 0 <= action <= 8
        act_lower = action % 3
        act_upper = action // 3

        if act_lower == 1:
            self.lowerlim -= self.limdelta
        elif act_lower == 2:
            self.lowerlim += self.limdelta
        
        if act_upper == 1:
            self.upperlim -= self.limdelta
        elif act_upper == 2:
            self.upperlim += self.limdelta

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
        infos = {'pnet': pnet}
        report = ''

        if __debug__:
            report += f'Demand: {pnet:8.2f} kW, '

        self._execute_action(action)

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

        infos['pbought'] = pbought
        infos['soc'] = self.ehub.get_soc()
        cost = price * pbought / 100
        reward = -cost

        if __debug__:
            maxsoc = self.ehub.get_maxsoc()
            soc = infos['soc']
            if len(self.ehub.storages) > 0:
                report += f'SOC: {soc:8.2f} kWh ({soc/maxsoc*100:6.2f}%) '
            else:
                report += 'SOC:     0.00 kWh (0%) '
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

    def _compute_capex_opex(self):
        '''Computes the capital and the operational expenses of the energy hub buy first
        determining the length of the period'''
        start = self.df.iloc[0]['ReadTimestamp']
        end = self.df.iloc[-1]['ReadTimestamp']
        delta = end - start # simulation time
        delta = delta.days * 24 + delta.seconds // 60 // 60 # simulation in hours

        capex = self.env.ehub.get_capex(delta)
        opex = self.env.ehub.get_opex(delta)

        return capex, opex

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

    def run_const_limits(self, lowerlim, upperlim, create_log=False):
        '''Runs the simulation with constant upper and lower limits.
        Args:
            - lowerlim: lower limit for the peak-shaving.
            - upperlim: upper limit for the peak-shaving.
            - create_log: bool value whether to create log of power values.
        Returns:
            - total_costs: total cost accumulated during the simulation.
            - powers: log of pnet, pbought, and soc.
        '''
        total_costs = 0
        self.env.set_limits(lowerlim, upperlim)
        powers = []
        for _, datarow in self.df.iterrows():
            pnet = datarow['net']
            price = datarow['price (cents/kWh)']
            _, reward, _, infos = self.env.step(0, pnet, price)
            if create_log:
                powers.append((infos['pnet'], infos['pbought'], infos['soc']))
            total_costs += -reward

        capex, opex = self._compute_capex_opex()
        total_costs += capex + opex

        return total_costs, powers
    
    def run_dynamic_limits(self, lookahead=4, margin=.05, create_log=False):
        '''Runs a simulation where the upper and lower limits for peak-shaving changes
        dynamically based on the median of future net power demand values.
        Args:
            - lookahead: the amount of future power values considered for the median.
            - margin: distance of upper and lower limits from the median.
            - create_log: bool value whether to create log of power values.
        Returns:
            - total_costs: total cost accumulated during simulation.
            - powers: log of pnet, pbought, and soc.
        '''
        total_costs = 0
        powers = []
        for idx, datarow in self.df.iterrows():
            pmedian = self.df.iloc[idx:idx+lookahead]['net'].median()
            lowerlim = pmedian * (1 - margin)
            upperlim = pmedian * (1 + margin)
            self.env.set_limits(lowerlim, upperlim)

            pnet = datarow['net']
            price = datarow['price (cents/kWh)']
            _, reward, _, infos = self.env.step(0, pnet, price)
            if create_log:
                powers.append((infos['pnet'], infos['pbought'], infos['soc']))
            total_costs += -reward

        capex, opex = self._compute_capex_opex()
        total_costs += capex + opex

        return total_costs, powers
    
    def run_equalized_limits(self, lookahead=24, create_log=False):
        total_costs = 0
        powers = []
        for idx, datarow in self.df.iterrows():
            idxfrom = max(0, idx - lookahead)
            idxto = min(len(self.df) - 1, idx + lookahead)
            next_pnets = self.df.iloc[idxfrom:idxto]['net']
            lowerlim, upperlim = compute_limits(next_pnets)
            self.env.set_limits(lowerlim, upperlim)

            pnet = datarow['net']
            price = datarow['price (cents/kWh)']
            _, reward, _, infos = self.env.step(0, pnet, price)
            if create_log:
                powers.append((infos['pnet'], lowerlim, upperlim, infos['pbought'], infos['soc']))
            total_costs += -reward

        capex, opex = self._compute_capex_opex()
        total_costs += capex + opex

        return total_costs, powers

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
        'delta_limit': 1,
        'LiIonBattery': liion_cnt,
        'Flywheel': flywh_cnt,
        'Supercapacitor': sucap_cnt
    }
    sim = PeakShaveSim(config, df)
    total_costs, _ = sim.run_const_limits(lowerlim, upperlim)
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
        'delta_limit': 1,
        'LiIonBattery': liion_cnt,
        'Flywheel': flywh_cnt,
        'Supercapacitor': sucap_cnt
    }
    sim = PeakShaveSim(config, df)
    total_costs, _ = sim.run_dynamic_limits(lookahead, margin)
    return total_costs

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit_mode', type=str, default='const')
    parser.add_argument('--datafile', type=str, default='short.csv')
    parser.add_argument('--liion', type=int, default=3)
    parser.add_argument('--flywheel', type=int, default=3)
    parser.add_argument('--supercap', type=int, default=3)
    parser.add_argument('--lookahead', type=int, default=None)
    parser.add_argument('--margin', type=float, default=.05)

    args = parser.parse_args()

    if args.limit_mode not in {'const', 'dyn'}:
        raise Exception('--limit_mode must be either `const` or `dyn`!')
    if args.limit_mode == 'dyn' and args.lookahead is None:
        raise Exception('You must provide --lookahead if --limit_mode is `dyn`!')

    return args

def main():
    args = get_args()
    fname = '../data/' + args.datafile

    df = process_file(fname)
    if args.limit_mode == 'const':
        total_costs = pkshave_constlims_objective(df, args.liion, args.flywheel,
                                                  args.supercap, args.margin)
    elif args.limit_mode == 'dyn':
        total_costs = pkshave_dinlims_objective(df, args.liion, args.flywheel,
                                                args.supercap, args.lookahead,
                                                args.margin)
    print(total_costs)

def test_equalized_runs():
    df = process_file('../data/Sub71125.csv')
    config = {
        'delta_limit': 1,
        'LiIonBattery': 10,
        'Flywheel': 10,
        'Supercapacitor': 10
    }
    sim = PeakShaveSim(config, df)
    _, _ = sim.run_equalized_limits(create_log=True)

if __name__ == '__main__':
    test_equalized_runs()
