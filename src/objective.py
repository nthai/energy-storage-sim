import pandas as pd
from datetime import datetime
from batteries import EnergyHub

def objective(data: pd.DataFrame, timelimit, c1: int, c2: int, c3: int) -> float:
    '''Runs simulation of batteries given input data and simulation time.
    params:
        - data: pandas.DataFrame containing the input data
        - timelimit: length of simulation in hours
        - c1: number of Li-ion batteries in the Energy Hub
        - c2: number of flywheel electricity storages in the Energy Hub
        - c3: number of supercapacitors in the Energy Hub
    
    returns: (float) the total cost generated using the greedy algorithm
    '''

    ehub = EnergyHub({
        'LiIonBattery': c1,
        'Flywheel': c2,
        'Supercapacitor': c3
    })

    start_time = None
    timeperiod = 0
    energy_cost = 0

    for _, row in data.iterrows():
        time, pv, load, pbuy = row
        psell = pbuy / 2
        
        if start_time is None:
            start_time = datetime.strptime(time, '%m%d%Y %H:%M')
        time = datetime.strptime(time, '%m%d%Y %H:%M')
        delta = time - start_time
        timeperiod = delta.days * 24 + delta.seconds / 60 / 60

        if timeperiod > timelimit:
            timeperiod = timelimit
            break

        pnet = pv - load
        pnet = ehub.step(pnet)
        if pnet > 0:
            energy_cost -= pnet * psell
        else:
            energy_cost += abs(pnet) * pbuy
    energy_cost /= 100

    capex = ehub.get_capex(timeperiod)
    opex = ehub.get_opex(timeperiod)
    total_cost = energy_cost + capex + opex

    print(f'Time period: {timeperiod}, ' +
          f'Total cost: {total_cost}, ' +
          f'Energy cost: {energy_cost:.2f}, ' +
          f'Capex: {capex:.2f}, Opex: {opex:.2f}')

    return total_cost

def main():
    df = pd.read_csv('../data/short.csv')
    cost = objective(df, float('inf'), 3, 3, 3)
    print(f'total cost: {cost}')

if __name__ == '__main__':
    main()
