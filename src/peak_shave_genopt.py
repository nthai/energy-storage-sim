import pygad
import pandas as pd
from peak_shave_sim import pkshave_constlims_objective
from peak_shave_sim import pkshave_dinlims_objective

FILENAME = '../data/full.csv'
DF = pd.read_csv(FILENAME)
DF['timestamp'] = pd.to_datetime(DF['timestamp'],
                                    format='%m%d%Y %H:%M')
DF['net'] = DF['Load (kWh)'] - DF['PV (kWh)']

def fitness_const(sol, sol_idx):
    liion_cnt = sol[0]
    flywh_cnt = sol[1]
    sucap_cnt = sol[2]
    margin = sol[3]
    cost = pkshave_constlims_objective(DF, liion_cnt, flywh_cnt, sucap_cnt, margin)
    return 10000000/cost

def fitness_dynamic(sol, sol_idx):
    liion_cnt = sol[0]
    flywh_cnt = sol[1]
    sucap_cnt = sol[2]
    lookahead = sol[3]
    margin = sol[4]
    cost = pkshave_dinlims_objective(DF, liion_cnt, flywh_cnt, sucap_cnt, lookahead,
                                     margin)
    return 10000000/cost

def on_generation(ga_instance: pygad.GA):
    sol, fit, _ = ga_instance.best_solution()
    print(f'sol: {sol}, fitness value: {fit}')

def optimize_const_limit_objective(config):
    config['fitness_func'] = fitness_const
    config['num_genes'] = 4
    config['gene_type'] = [int, int, int, float]
    config['gene_space'] = [{'low': 0, 'high': 50},
                            {'low': 0, 'high': 50},
                            {'low': 0, 'high': 50},
                            {'low': 0, 'high': 1}]

    ga_instance = pygad.GA(**config)
    ga_instance.run()

    sol, sol_fitness, sol_idx = ga_instance.best_solution()
    print(f'Solution: {sol}')
    print(f'Fitness: {sol_fitness}')

def optimize_dynamic_limit_objective(config):
    config['fitness_func'] = fitness_dynamic
    config['num_genes'] = 5
    config['gene_type'] = [int, int, int, int, float]
    config['gene_space'] = [{'low': 0, 'high': 50},
                            {'low': 0, 'high': 50},
                            {'low': 0, 'high': 50},
                            list(range(4, 25, 4)),
                            {'low': 0, 'high': 1}]

    ga_instance = pygad.GA(**config)
    ga_instance.run()

    sol, sol_fitness, sol_idx = ga_instance.best_solution()
    print(f'Solution: {sol}')
    print(f'Fitness: {sol_fitness}')

def main():
    config = {
        'on_generation': on_generation,
        'num_generations': 500,
        'num_parents_mating': 8,
        'sol_per_pop': 10,
        'init_range_low': 0,
        'init_range_high': 50,
        'parent_selection_type': 'sss',
        'keep_parents': 2,
        'crossover_type': 'single_point',
        'mutation_type': 'random',
        'mutation_percent_genes': 50
    }
    optimize_const_limit_objective(config)
    optimize_dynamic_limit_objective(config)


if __name__ == '__main__':
    main()
