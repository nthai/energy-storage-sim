import argparse
from typing import Type
import gym
import pandas as pd
from batteries import EnergyHub
from greedy import GreedySim
from util import process_file
from util import compute_limits
from util import calc_fluctuation
from util import calc_periodic_fluctuation
from util import calc_peak_power_sum
from util import is_peak

class PeakShaveEnv(gym.Env):
    def __init__(self, config: dict) -> None:
        super().__init__()

        self.limdelta = config['delta_limit']
        self.upperlim = 3000
        self.lowerlim = 1000
        self.ehub = EnergyHub(config)

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

    def step(self, action: int, pnet: float, price: float, verbose=False):
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

        if __debug__ and verbose:
            report += f'Demand: {pnet:8.2f} kW, '

        self._execute_action(action)

        pbought = 0
        total_penalty = 0
        if pnet > self.upperlim:
            # the demand is higher than the upper limit, take energy from the battery
            pdischarge = pnet - self.upperlim
            total_discharge, total_selfdischarge, total_penalty = self.ehub.discharge(pdischarge)
            pbought = pnet - total_discharge

            if __debug__ and verbose:
                report += (f'Purchased: {pbought:8.2f} kW, ')
                report += (f'Discharged: {total_discharge:6.2f} kW, ' +
                           f'SelfD: {total_selfdischarge:6.2f} kW ')
        elif pnet < self.lowerlim:
            # the demand is lower than the lower limit, use the excess to charge
            # the battery
            pcharge = self.lowerlim - pnet
            total_charge, total_selfdischarge, total_penalty = self.ehub.charge(pcharge)
            pbought = pnet + total_charge

            if __debug__ and verbose:
                report += (f'Purchased: {pbought:8.2f} kW, ')
                report += (f'Charged:    {total_charge:6.2f} kW, ' +
                           f'SelfD: {total_selfdischarge:6.2f} kW ')
        else:
            # we do nothing, but there is still self-discharge!
            _, _, total_selfdischarge = self.ehub.do_nothing()
            pbought = pnet

            if __debug__ and verbose:
                report += (f'Purchased: {pbought:8.2f} kW, ')
                report += (f'No charge/discharge,   ' +
                           f'SelfD: {total_selfdischarge:6.2f} kW ')

        infos['pbought'] = pbought
        infos['soc'] = self.ehub.get_soc()
        cost = price * pbought / 100
        reward = -cost - total_penalty

        if __debug__ and verbose:
            maxsoc = self.ehub.get_maxsoc()
            soc = infos['soc']
            if len(self.ehub.storages) > 0:
                report += f'SOC: {soc:8.2f} kWh ({soc/maxsoc*100:6.2f}%) '
            else:
                report += 'SOC:     0.00 kWh (0%) '
            report += f'Price: {price:7.2f} '
            report += f'Money spent: {cost:7.2f} '
            report += f'Total pen.: {total_penalty:7.2f}'
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

    def _compute_capex_opex(self) -> tuple[float, float]:
        '''Computes the capital and the operational expenses of the energy hub by first
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

    def _get_limits(self, **kwargs):
        raise NotImplementedError()

    def run(self, **kwargs):
        verbose = False if 'verbose' not in kwargs.keys() else kwargs['verbose']

        energy_costs, total_costs = 0, 0
        powers = []

        for idx, datarow in self.df.iterrows():
            lowerlim, upperlim = self._get_limits(idx=idx, datarow=datarow, **kwargs)
            self.env.set_limits(lowerlim, upperlim)

            pnet = datarow['net']
            price = datarow['price (cents/kWh)']
            _, reward, _, infos = self.env.step(0, pnet, price, verbose=verbose)
            powers.append((datarow['timestamp'], infos['pnet'], infos['pbought'],
                           infos['soc'], lowerlim, upperlim))
            energy_costs += -reward
        
        capex, opex = self._compute_capex_opex()
        total_costs += capex + opex + energy_costs

        costs = {
            'energy_costs': energy_costs,
            'capex': capex,
            'opex': opex,
            'total_costs': total_costs
        }

        return costs, powers

class ConstLimPeakShaveSim(PeakShaveSim):
    '''Peak-shave simulation with constant limits.
    Adjustable args:
        - margin: Margin from the mean of the data'''

    def _get_limits(self, **kwargs):
        return self.lowerlim, self.upperlim
    
    def run(self, **kwargs):
        self.margin = kwargs['margin']
        mean_demand = self.df['net'].mean()
        self.upperlim = mean_demand * (1 + self.margin)
        self.lowerlim = mean_demand * (1 - self.margin)
        return super().run(**kwargs)

class DynamicLimPeakShaveSim(PeakShaveSim):
    '''Peak-shave simulation with dynamically changing upper and lower limits. The
    algorithm looks ahead into the future (e.g. through prediction) and determines
    the upper and lower limits that are a margin distance from the median.
    Adjustable parameters:
        - lookahead: the amount of future steps used to determine the median.
        - margin: distance of the upper and lower limit from the median in percentage.
    '''

    def _get_limits(self, **kwargs):
        idx = kwargs['idx']
        lookahead = kwargs['lookahead']
        margin = kwargs['margin']

        pmedian = self.df.iloc[idx:idx+lookahead]['net'].median()
        lowerlim = pmedian * (1 - margin)
        upperlim = pmedian * (1 + margin)
        return lowerlim, upperlim

class EqualizedLimPeakShaveSim(PeakShaveSim):
    '''Peak-shave simulation with dynamically changing upper and lower limits. The
    algorithm looks ahead into the future (e.g. through prediction) and computes the
    upper and lower limits with a given margin distance for which the area above the
    upper limit equals the area below the lowerlimit. The size of margin is set to
    be 1/3.
    Adjustable parameters:
        - lookahead: the amount of future steps used to compute the limits.
        - tolerance: the limit computing algorithm stops if the difference between
            the areas under the curve is below the tolerance level (in kWh).
    '''
    def _get_limits(self, **kwargs):
        idx = kwargs['idx']
        lookahead = kwargs['lookahead']
        tolerance = 2 if 'tolerance' not in kwargs else kwargs['tolerance']

        idxfrom = max(0, idx - lookahead)
        idxto = min(len(self.df) - 1, idx + lookahead)
        next_pnets = self.df.iloc[idxfrom:idxto]['net']
        
        lowerlim, upperlim = compute_limits(next_pnets, tolerance)
        return lowerlim, upperlim

def objective(SimClass: Type[PeakShaveSim], df: pd.DataFrame, liion_cnt: int,
              flywh_cnt: int, sucap_cnt: int, **run_config):
    '''Objective function for the peak-shave optimization problem.
    Args:
        - SimClass: class of simulation type to run. E.g.: ConstLimPeakShaveSim
        - df: pandas.DataFrame containing the price data and the net power data
            under the `net` key.
        - liion_cnt: number of LiIon batteries
        - flywh_cnt: number of flywheel batteries
        - sucap_cnt: number of supercapacitors
        - **run_config: value fed to the class's run method.

    Returns:
        - costs: dict containing amount spent on buying electricity from the grid.
        - metrics: dict containing the following metrics: `fluctuation`,
            `mean_periodic_fluctuation`, `peak_power_sum`, `peak_power_count`
    '''
    config = {
        'delta_limit': 1,
        'LiIonBattery': liion_cnt,
        'Flywheel': flywh_cnt,
        'Supercapacitor': sucap_cnt
    }
    sim = SimClass(config, df)
    costs, powers = sim.run(**run_config)

    metrics = {
        'fluctuation': calc_fluctuation(powers),
        'mean_periodic_fluctuation': calc_periodic_fluctuation(powers)
    }

    if SimClass is not GreedySim:
        ppsum, ppcount = calc_peak_power_sum(powers)
        metrics['peak_power_sum'] = ppsum
        metrics['peak_power_count'] = ppcount

    return costs, metrics

def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit_mode', type=str, default='const')
    parser.add_argument('--datafile', type=str, default='../data/Sub71125.csv')
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

def observe_powers(powers: list, df_log=False):
    for idx, power in enumerate(powers):
        if df_log:
            power = list(power)
            if is_peak(powers, idx, 10):
                power.append(1)
            else:
                power.append(0)
            print(','.join(map(str, power)))
        else:
            print(
                f'{power[0]} - ' +
                f'net: {power[1]:4.1f} - ' +
                f'bought: {power[2]:6.2f} - ' +
                f'soc: {power[3]:6.2f} - ' +
                f'lower: {power[4]:6.2f} - ' +
                f'upper: {power[5]:6.2f} - ' +
                (f'peak! ' if is_peak(powers, idx, 10) else '')
            )

def test_sim(SimClass: Type[PeakShaveSim], run_type: str, **sim_run_config):
    df = process_file('../data/Sub71125.csv')
    config = {
        'delta_limit': 1,
        'LiIonBattery': 2,
        'Flywheel': 3,
        'Supercapacitor': 0,
    }
    sim = SimClass(config, df)
    costs, powers = sim.run(**sim_run_config)

    if __debug__:
        observe_powers(powers, True)

    ppsum, ppcount = calc_peak_power_sum(powers)
    metrics = {
        'fluctuation': calc_fluctuation(powers),
        'mean_periodic_fluctuation': calc_periodic_fluctuation(powers),
        'peak_power_sum': ppsum,
        'peak_power_count': ppcount
    }

    print()
    print(f'{run_type} run energy costs: {costs["energy_costs"]:.2f} ' +
          f'capex: {costs["capex"]:.2f} opex: {costs["opex"]:.2f} ' +
          f'total costs: {costs["total_costs"]:.2f}')
    print(f'Fluctuation: {metrics["fluctuation"]:.2f} ' +
          f'Mean periodic fluctuation: {metrics["mean_periodic_fluctuation"]:.2f} ' +
          f'Peak above upper limit sum: {metrics["peak_power_sum"]:.2f} ' +
          f'count: {metrics["peak_power_count"]}')

def test_objective(SimClass: Type[PeakShaveSim], **run_config):
    args = get_args()
    df = process_file(args.datafile)

    costs, metrics = objective(SimClass, df, args.liion, args.flywheel, args.supercap,
                               **run_config)
    print(costs)
    print(metrics)
    print()

def main():
    # test_sim(ConstLimPeakShaveSim, 'Const', margin=.02, penalize_charging=True, create_log=True, verbose=True)
    # test_sim(DynamicLimPeakShaveSim, 'Dynamic', lookahead=24, margin=.05, penalize_charging=True, create_log=True)
    test_sim(EqualizedLimPeakShaveSim, 'Equalized', lookahead=24, penalize_charging=True, create_log=True)

    # test_objective(ConstLimPeakShaveSim, margin=.02, penalize_charging=True, create_log=True)
    # test_objective(DynamicLimPeakShaveSim, lookahead=24, margin=.05, penalize_charging=True, create_log=True)
    # test_objective(EqualizedLimPeakShaveSim, lookahead=24, penalize_charging=True, create_log=True)

if __name__ == '__main__':
    main()
