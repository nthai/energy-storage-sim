import gym
import pandas as pd

FILENAME = '../data/short.csv'

class PeakShaveEnv(gym.Env):
    def __init__(self, config) -> None:
        super().__init__()

        self.df = self._read_df(config['filename'])
        self.upperlim = config['Plim_upper']
        self.lowerlim = config['Plim_lower']

        self.reset()

    def reset(self):
        self.timestep = 0
        self.maxtime = len(self.df)
        self.soc = 0

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

        # pnet is the power demand. self.df.iat[self.timestep, 4] is the same as
        # self.df.iloc[self.timestep]['net']
        tdelta = 1
        pnet = self.df.iat[self.timestep, 4] / tdelta
        if pnet > self.upperlim:
            # the demand is higher than the upper limit, take energy from the battery
            pdcharge = pnet - self.upperlim
            if pdcharge * tdelta > self.soc:
                # discharge everything
                p = pdcharge * tdelta - self.soc
                self.soc = 0

                # compute power bought from the grid
                pgrid = self.upperlim + p
            else:
                # discharge only the necessary amount
                self.soc = self.soc - pdcharge * tdelta

                # power bought from 
        elif pnet < self.lowerlim:
            # the demand is lower than the lower limit, use the excess to charge
            # the battery
            pass
        else:
            # do nothing?
            pass
        
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
        'Plim_lower': 80
    }

    sim = PeakShaveSim(config)
    sim.run()

if __name__ == '__main__':
    main()
