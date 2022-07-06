import gym
import pandas as pd
from peak_shave_battery import PeakShaveEnergyHub

FILENAME = '../data/short.csv'

class PeakShaveEnv(gym.Env):
    def __init__(self, config) -> None:
        super().__init__()

        self.df = self._read_df(config['filename'])
        self.upperlim = config['Plim_upper']
        self.lowerlim = config['Plim_lower']
        self.ehub = PeakShaveEnergyHub(config)

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

    def step(self, action):
        state = None
        reward = None
        infos = None

        report = ''

        # pnet is the power demand. self.df.iat[self.timestep, 4] is the same as
        # self.df.iloc[self.timestep]['net']
        tdelta = 1
        pnet = self.df.iat[self.timestep, 4] / tdelta
        if pnet > self.upperlim:
            # the demand is higher than the upper limit, take energy from the battery
            pdischarge = pnet - self.upperlim
            total_discharge, total_selfdischarge = self.ehub.discharge(pdischarge)
            report += (f'Net power: {pnet:8.2f} kW, ' +
                       f'Discharged: {total_discharge:6.2f} kW, ' +
                       f'Self-discharged: {total_selfdischarge:6.2f} kW ')
        elif pnet < self.lowerlim:
            # the demand is lower than the lower limit, use the excess to charge
            # the battery
            pcharge = self.lowerlim - pnet
            total_charge, total_selfdischarge = self.ehub.charge(pcharge)
            report += (f'Net power: {pnet:8.2f} kW, ' +
                       f'Charged:    {total_charge:6.2f} kW, ' +
                       f'Self-discharged: {total_selfdischarge:6.2f} kW ')
        else:
            # do nothing
            pass

        report += f'State-of-Charge: {self.ehub.get_soc():8.2f} kWh '
        print(report)

        self.timestep += 1

        done = (self.timestep >= self.maxtime)
        return state, reward, done, infos

class PeakShaveSim:
    def __init__(self, config):
        self.env = PeakShaveEnv(config)

    def run(self):
        while not (obs := self.env.step(0))[2]:
            pass

def main():
    config = {
        'filename': FILENAME,
        'Plim_upper': 120,
        'Plim_lower': 80,
        'LiIonBattery': 3,
        'Flywheel': 3,
        'Supercapacitor': 3
    }

    sim = PeakShaveSim(config)
    sim.run()

if __name__ == '__main__':
    main()
