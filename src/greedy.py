import numpy as np
from concurrent.futures import process
from peak_shave_battery import PeakShaveEnergyHub
from util import process_file
import os

FILEPATH = os.path.dirname(os.path.abspath(__file__))

class GreedySim():
    def __init__(self, config: dict, df=None) -> None:
        super().__init__()

        self.df = process_file(config['datafile']) if df is None else df
        self.ehub = PeakShaveEnergyHub(config)
        self.reset()

    def reset(self):
        self.ehub.reset()

    def _compute_capex_opex(self):
        '''Computes the capital and the operational expenses of the energy hub by first
        determining the length of the period'''
        start = self.df.iloc[0]['ReadTimestamp']
        end = self.df.iloc[-1]['ReadTimestamp']
        delta = end - start # simulation time
        delta = delta.days * 24 + delta.seconds // 60 // 60 # simulation in hours

        capex = self.ehub.get_capex(delta)
        opex = self.ehub.get_opex(delta)

        return capex, opex

    def run(self):
        energy_cost = 0
        for idx, datarow in self.df.iterrows():
            if __debug__:
                print(f'{idx:3d} {datarow["net"]:5.1f}')

            pbought = 0
            pnets = list(self.df.iloc[idx:]['net'])

            # find how much time we could last with current battery charge
            treserve = self.ehub.compute_reserve_time(pnets)

            if __debug__:
                print(f'\ttreserve: {treserve}')

            # find the lowest electricity price within the given time frame
            prices = self.df.iloc[idx:idx+treserve+1]['price (cents/kWh)']
            min_id = np.argmin(prices)
            
            if __debug__:
                print(f'\telectricity prices: {list(prices)}')
                print(f'\tlowest electricity price at: {min_id}')

            # if the lowest price is now
            if min_id == 0:
                # see how much power we need to charge up completely
                pneed = self.ehub.power_to_max()
                # buy that power
                pbought += pneed * prices.iloc[0] / 100
                # use it to charge the ehub
                self.ehub.charge(pneed)
                if __debug__:
                    print(f'\tWe need to charge!')
                    print(f'\tcharge {pneed:.2f} kWh!')

            # discharge
            self.ehub.discharge(datarow['net'])
            if __debug__:
                print(f'\tdischarge: {datarow["net"]:.2f}')
                print(f'\tnew soc: {self.ehub.get_soc():.2f}')
            energy_cost += pbought
        capex, opex = self._compute_capex_opex()
        costs = {
            'energy_cost': energy_cost,
            'capex': capex,
            'opex': opex,
            'total_costs': energy_cost + capex + opex
        }
        return costs

def test_greedy_sim():
    config = {
        'datafile': FILEPATH + '/../data/Sub71125.csv',
        'LiIonBattery': 1,
        'Flywheel': 0,
        'Supercapacitor': 0
    }

    sim = GreedySim(config)
    costs = sim.run()
    print(costs)

if __name__ == '__main__':
    test_greedy_sim()
