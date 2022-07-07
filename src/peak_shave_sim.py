import gym
import pandas as pd
from peak_shave_battery import PeakShaveEnergyHub

FILENAME = '../data/short.csv'

class PeakShaveEnv(gym.Env):
    def __init__(self, config) -> None:
        super().__init__()

        # self.df = self._read_df(config['filename'])
        self.limdelta = config['delta_limit']
        self.upperlim = config['Plim_upper']
        self.lowerlim = config['Plim_lower']
        self.ehub = PeakShaveEnergyHub(config)

        if self.upperlim < self.lowerlim:
            raise Exception(f'Upper limit ({self.upperlim}) is lower than ' +
                            f'the lower limit ({self.lowerlim}!)')

        self.reset()

    def reset(self):
        # self.timestep = 0
        # self.maxtime = len(self.df)
        self.ehub.reset()

    # def _read_df(self, fname: str) -> pd.DataFrame:
    #     df = pd.read_csv(fname)
    #     df['timestamp'] = pd.to_datetime(df['timestamp'],
    #                                      format='%m%d%Y %H:%M')
    #     df['net'] = df['Load (kWh)'] - df['PV (kWh)']
    #     return df

    def get_available_actions(self):
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

    def step(self, action, pnet, price):
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
    def __init__(self, config):
        self.env = PeakShaveEnv(config)
        self.df = self._read_df(config['filename'])
        
    def _read_df(self, fname: str) -> pd.DataFrame:
        df = pd.read_csv(fname)
        df['timestamp'] = pd.to_datetime(df['timestamp'],
                                         format='%m%d%Y %H:%M')
        df['net'] = df['Load (kWh)'] - df['PV (kWh)']
        return df

    def run(self):
        total_costs = 0
        for _, datarow in self.df.iterrows():
            pnet = datarow['net']
            price = datarow['price (cents/kWh)']
            _, reward, _, _ = self.env.step(0, pnet, price)
            total_costs += -reward
        print(f'Total Cost: {total_costs}')

def main():
    config = {
        'filename': FILENAME,
        'Plim_upper': 2500,
        'Plim_lower': 1000,
        'delta_limit': 1,
        'LiIonBattery': 3,
        'Flywheel': 3,
        'Supercapacitor': 3
    }

    sim = PeakShaveSim(config)
    sim.run()

if __name__ == '__main__':
    main()
