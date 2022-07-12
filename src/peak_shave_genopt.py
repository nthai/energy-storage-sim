import argparse
import pygad
import pandas as pd
from peak_shave_sim import pkshave_constlims_objective
from peak_shave_sim import pkshave_dinlims_objective
from util import process_file

DF = None

def fitness_const(sol, sol_idx) -> float:
    '''Fitness function for the genetic algorithm to optimize for constant upper and
    lower limit in the peak-shaving algorithm.'''
    liion_cnt = sol[0]
    flywh_cnt = sol[1]
    sucap_cnt = sol[2]
    margin = sol[3]
    cost = pkshave_constlims_objective(DF, liion_cnt, flywh_cnt, sucap_cnt, margin)
    return 10000000/cost

def fitness_dynamic(sol, sol_idx) -> float:
    '''Fitness function for the genetic algorithm to optimize for dynamically
    changing upper and lower limits for the peak-shaving algorithm. Limits change
    according to the median of future net power demand values.'''
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

def parse_config() -> dict:
    parser = argparse.ArgumentParser(description='Run genetic algorithm to optimize' +
                                     ' peak-shave.')
    parser.add_argument('--limit_mode', type=str, default='const',
                        help='Determines how the upper and lower limit should be ' +
                        'set. Upper and lower limit are set at the start in case' +
                        ' of `const` or set dynamically at each timestep in case' +
                        ' of `dyn`.')
    parser.add_argument('--num_generations', type=int, default=500,
                        help='Number of generations in the genetic algorithm.')
    parser.add_argument('--sol_per_pop', type=int, default=10,
                        help='Number of solutions per population.')
    parser.add_argument('--datafile', type=str, default='short.csv',
                        help='Name of the file used as source data. File has to ' +
                        'be in the data folder.')
    args = parser.parse_args()

    if args.limit_mode not in {'const', 'dyn'}:
        raise Exception('--limit_mode must be either `const` or `dyn`!')

    config = {
        'datafile': args.datafile,
        'limit_mode': args.limit_mode,
        'on_generation': on_generation,
        'num_generations': args.num_generations,
        'num_parents_mating': 8,
        'sol_per_pop': args.sol_per_pop,
        'init_range_low': 0,
        'init_range_high': 50,
        'parent_selection_type': 'sss',
        'keep_parents': 2,
        'crossover_type': 'single_point',
        'mutation_type': 'random',
        'mutation_percent_genes': 50
    }
    return config

def main(config):
    opt_config = {k: v for k, v in config.items() if k not in {'limit_mode', 'datafile'}}
    if config['limit_mode'] == 'const':
        optimize_const_limit_objective(opt_config)
    elif config['limit_mode'] == 'dyn':
        optimize_dynamic_limit_objective(opt_config)

def set_global_dataframe(fname):
    global DF

    print(f'Set dataframe from file: {fname}')
    DF = process_file(fname)

if __name__ == '__main__':
    config = parse_config()
    set_global_dataframe('../data/' + config['datafile'])
    main(config)
