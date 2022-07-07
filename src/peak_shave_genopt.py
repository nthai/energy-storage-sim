import pygad
import pandas as pd
from peak_shave_sim import peak_shave_objective

FILENAME = '../data/full.csv'
DF = pd.read_csv(FILENAME)
DF['timestamp'] = pd.to_datetime(DF['timestamp'],
                                    format='%m%d%Y %H:%M')
DF['net'] = DF['Load (kWh)'] - DF['PV (kWh)']

def fitness(sol, sol_idx):
    liion_cnt = sol[0]
    flywh_cnt = sol[1]
    sucap_cnt = sol[2]
    margin = sol[3]
    cost = peak_shave_objective(DF, liion_cnt, flywh_cnt, sucap_cnt, margin)
    return 10000/cost

def on_generation(ga_instance: pygad.GA):
    sol, fit, _ = ga_instance.best_solution()
    print(f'sol: {sol}, fitness value: {fit}')

def main():
    config = {
        # 'fitness_func': obj,
        'fitness_func': fitness,
        'on_generation': on_generation,
        'num_generations': 100,
        'num_parents_mating': 8,
        'sol_per_pop': 10,
        'num_genes': 4,
        'init_range_low': 0,
        'init_range_high': 50,
        'parent_selection_type': 'sss',
        'keep_parents': 2,
        'crossover_type': 'single_point',
        'mutation_type': 'random',
        'mutation_percent_genes': 50,
        'gene_type': [int, int, int, float],
        'gene_space': [{'low': 0, 'high': 50},
                       {'low': 0, 'high': 50},
                       {'low': 0, 'high': 50},
                       {'low': 0, 'high': 1}]
    }

    ga_instance = pygad.GA(**config)
    ga_instance.run()

    sol, sol_fitness, sol_idx = ga_instance.best_solution()
    print(f'Solution: {sol}')
    print(f'Fitness: {sol_fitness}')

if __name__ == '__main__':
    main()
