import re

p1 = re.compile(r"[\D]*'LiIonBattery': (\d*), 'Flywheel': (\d*), 'Supercapacitor': (\d*)}")
p2 = re.compile(r"Time period: ([\d.]*), Energy cost: ([\d.]*), Capex: ([\d.]*), Opex: ([\d.]*)")

def get_results(fname: str) -> dict:
    key = None
    cols = ['time', 'energy_cost', 'capex', 'opex']
    results = dict()
    with open(fname) as infile:
        for idx, line in enumerate(infile):
            line = line.strip()
            
            if m := p1.match(line):
                key = tuple(map(int, m.groups()))
            elif m := p2.match(line):
                if key is not None:
                    results[key] = dict(zip(cols, tuple(map(float, m.groups()))))
                    key = None
                else:
                    print(line)
                    raise Exception()
    return results

def main():
    results = get_results('nohup.out')
    print(min(results, key=lambda x: results[x]['energy_cost'] + results[x]['capex'] + results[x]['opex']))

if __name__ == '__main__':
    main()
