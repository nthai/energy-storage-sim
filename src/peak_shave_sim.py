import gym
import pandas as pd
from peak_shave_battery import PeakShaveEnergyHub

# FILENAME = '../data/short.csv'
FILENAME = '/home/nthai/codes/github/ml/energy-storage-sim/data/short.csv'

class PeakShaveEnv(gym.Env):
    def __init__(self, config) -> None:
        super().__init__()

        self.df = self._read_df(config['filename'])
        self.limdelta = config['delta_limit']
        self.upperlim = config['Plim_upper']
        self.lowerlim = config['Plim_lower']
        self.ehub = PeakShaveEnergyHub(config)

        if self.upperlim < self.lowerlim:
            raise Exception(f'Upper limit ({self.upperlim}) is lower than ' +
                            f'the lower limit ({self.lowerlim}!)')

        self.reset()

    def reset(self):
        self.timestep = 0
        self.maxtime = len(self.df)
        self.ehub.reset()

    def _read_df(self, fname: str) -> pd.DataFrame:
        df = pd.read_csv(fname)
        df['timestamp'] = pd.to_datetime(df['timestamp'],
                                         format='%m%d%Y %H:%M')
        df['net'] = df['Load (kWh)'] - df['PV (kWh)']
        return df

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

    def step(self, action):
        state = None
        reward = None
        infos = []

        # pnet is the power demand. self.df.iat[self.timestep, 4] is the same as
        # self.df.iloc[self.timestep]['net']
        tdelta = 1
        pnet = self.df.iat[self.timestep, 4] / tdelta
        report = f'Net demand: {pnet:8.2f} kW, '
        infos += [pnet]
        if pnet > self.upperlim:
            # the demand is higher than the upper limit, take energy from the battery
            pdischarge = pnet - self.upperlim
            total_discharge, total_selfdischarge = self.ehub.discharge(pdischarge)
            pbought = pnet - total_discharge
            report += (f'Purchased: {pbought:8.2f} kW, ')
            report += (f'Discharged: {total_discharge:6.2f} kW, ' +
                       f'Self-discharged: {total_selfdischarge:6.2f} kW ')
        elif pnet < self.lowerlim:
            # the demand is lower than the lower limit, use the excess to charge
            # the battery
            pcharge = self.lowerlim - pnet
            total_charge, total_selfdischarge = self.ehub.charge(pcharge)
            pbought = pnet + total_charge
            report += (f'Purchased: {pbought:8.2f} kW, ')
            report += (f'Charged:    {total_charge:6.2f} kW, ' +
                       f'Self-discharged: {total_selfdischarge:6.2f} kW ')
        else:
            _, _, total_selfdischarge = self.ehub.do_nothing()
            pbought = pnet
            report += (f'Purchased: {pbought:8.2f} kW, ')
            report += (f'No charge/discharge,   ' +
                       f'Self-discharged: {total_selfdischarge:6.2f} kW ')
            
        maxsoc = self.ehub.get_maxsoc()
        soc = self.ehub.get_soc()
        report += f'State-of-Charge: {soc:8.2f} kWh ({soc/maxsoc*100:.2f}%)'
        print(report)

        self.timestep += 1

        done = (self.timestep >= self.maxtime)
        return state, reward, done, infos

class PeakShaveSim:
    def __init__(self, config):
        self.env = PeakShaveEnv(config)

    def run(self):
        cnt = 0
        while not (obs := self.env.step(0))[2]:
            pass

def main():
    config = {
        'filename': FILENAME,
        'Plim_upper': 2000,
        'Plim_lower': 1500,
        'delta_limit': 1,
        'LiIonBattery': 3,
        'Flywheel': 3,
        'Supercapacitor': 3
    }

    sim = PeakShaveSim(config)
    sim.run()

if __name__ == '__main__':
    main()
