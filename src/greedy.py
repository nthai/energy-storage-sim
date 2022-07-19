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

    def run(self):
        total_cost = 0
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
                pbought += pneed
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
            total_cost += pbought
        print(f'Total cost: {total_cost}')

def test_greedy_sim():
    config = {
        'datafile': FILEPATH + '/../data/Sub71125.csv',
        'LiIonBattery': 10,
        'Flywheel': 10,
        'Supercapacitor': 10
    }

    sim = GreedySim(config)
    sim.run()
if __name__ == '__main__':
    test_greedy_sim()
