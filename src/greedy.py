from concurrent.futures import process
from peak_shave_battery import PeakShaveEnergyHub
from util import process_file

class GreedySim():
    def __init__(self, config: dict, df=None) -> None:
        super().__init__()

        self.df = process_file(config['datafile']) if df is None else df
        self.ehub = PeakShaveEnergyHub(config)
        self.reset()

    def reset(self):
        self.ehub.reset()

    def run(self):
        for idx, datarow in self.df.iterrows():
            pbought = 0
            pnets = list(self.df.iloc[idx:]['net'])
            treserve = self.ehub.compute_reserve_time(pnets)
            tfull = self.ehub.compute_full_reserve(pnets)
            print(treserve, tfull)

def test_greedy_sim():
    config = {
        'datafile': '../data/Sub71125.csv',
        'LiIonBattery': 10,
        'Flywheel': 10,
        'Supercapacitor': 10
    }

    sim = GreedySim(config)
    sim.run()
if __name__ == '__main__':
    test_greedy_sim()
