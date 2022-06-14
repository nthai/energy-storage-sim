from batteries import EnergyHub

DATAFILENAME = '../data/full.csv'
EHUB_CONFIG = {
    'LiIonBattery': 10,
    'Flywheel': 0,
    'Supercapacitor': 0
}

def main():
    ehub = EnergyHub(EHUB_CONFIG)
    total_cost = 0
    with open(DATAFILENAME) as datafile:
        for idx, line in enumerate(datafile):
            if idx == 0: continue
            pv, load, price = map(float, line.strip().split(',')[1:])
            pnet = pv - load
            pnet = ehub.step(pnet)
            if pnet > 0:
                total_cost -= pnet * price / 2
            else:
                total_cost += abs(pnet) * price
    total_cost = total_cost/100
    print(f'Total cost of energy: {total_cost:.4f} USD')
    print('Warning: this cost does not contain capex/opex for the energyhub yet.')

if __name__ == '__main__':
    main()
