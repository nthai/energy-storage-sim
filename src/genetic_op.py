
import argparse
import pygad
from greedy import GreedySim
from util import process_file
from peak_shave_sim import objective
from peak_shave_sim import ConstLimPeakShaveSim
from peak_shave_sim import DynamicLimPeakShaveSim
from peak_shave_sim import EqualizedLimPeakShaveSim

DF = None

def print_gene_fitness(liion_cnt, flywh_cnt, sucap_cnt, cost,
                       margin=None, lookahead=None):
    text = f'LiIon: {liion_cnt:3d} '
    text += f'Flywheel: {flywh_cnt:3d} '
    text += f'Supercapacitor: {sucap_cnt:3d} '
    if margin is not None:
        text += f'Margin: {margin:6.4f} '
    if lookahead is not None:
        text += f'Lookahead: {lookahead:3d} '
    text += f'Fitness: {100000/cost:.4f}'
    print(text)

def fitness_const(sol, _) -> float:
    '''Fitness function used for finding optimal parameters in case of constant
    limits.
    Args:
        - sol: solution list containing the genes.
            0. Number of LiIon batteries.
            1. Number of flywheel batteries.
            2. Number of supercapacitors.
            3. Margin, half of the distance between the upper and the lower limit.
    Returns: A value related to the total cost accumulated during simulation:
        100000/cost'''
    liion_cnt = sol[0]
    flywh_cnt = sol[1]
    sucap_cnt = sol[2]
    margin = sol[3]
    costs, metrics = objective(ConstLimPeakShaveSim, DF, liion_cnt, flywh_cnt,
                               sucap_cnt, margin=margin, penalize_charging=True,
                               create_log=False)

    # cost = costs['total_costs']
    # cost = metrics['fluctuation']
    cost = metrics['peak_power_sum']
    print_gene_fitness(liion_cnt, flywh_cnt, sucap_cnt, cost, margin)

    try:
        output = 100000/cost
    except:
        print(cost)
        raise


    return output

def fitness_dyn(sol, _) -> float:
    '''Fitness function used for finding optimal parameters in case of dynamically
    changing limits. Limits are computed based on the median of future values.
    Args:
        - sol: solution list containing the genes.
            0. Number of LiIon batteries.
            1. Number of flywheel batteries.
            2. Number of supercapacitors.
            3. Margin, half of the distance between the upper and the lower limit.
    Returns: A value related to the total cost accumulated during simulation:
        100000/cost'''
    liion_cnt = sol[0]
    flywh_cnt = sol[1]
    sucap_cnt = sol[2]
    margin = sol[3]
    lookahead = 24
    costs, metrics = objective(DynamicLimPeakShaveSim, DF, liion_cnt, flywh_cnt,
                               sucap_cnt, lookahead=lookahead, margin=margin,
                               penalize_charging=True, create_log=False)

    # cost = costs['total_costs']
    # cost = metrics['fluctuation']
    cost = metrics['peak_power_sum']
    print_gene_fitness(liion_cnt, flywh_cnt, sucap_cnt, cost, margin, lookahead)
    return 100000/cost

def fitness_eq(sol, _) -> float:
    '''Fitness function used for finding optimal parameters in case of dynamically
    changing limits. Limits are computed such that the area above the upper limit
    would equal the area below the lower limit. Computations are based on future
    values.
    Args:
        - sol: solution list containing the genes.
            0. Number of LiIon batteries.
            1. Number of flywheel batteries.
            2. Number of supercapacitors.
    Returns: A value related to the total cost accumulated during simulation:
        100000/cost'''
    liion_cnt = sol[0]
    flywh_cnt = sol[1]
    sucap_cnt = sol[2]
    lookahead = 24
    costs, metrics = objective(EqualizedLimPeakShaveSim, DF, liion_cnt, flywh_cnt,
                               sucap_cnt, lookahead=lookahead, penalize_charging=True,
                               create_log=False)
    # cost = costs['total_costs']
    # cost = metrics['fluctuation']
    cost = metrics['peak_power_sum']
    print_gene_fitness(liion_cnt, flywh_cnt, sucap_cnt, cost, lookahead=lookahead)
    return 100000/cost

def fitness_greedy(sol, _):
    '''Fitness function used for finding optimal parameters in case of the greedy
    algorithm.
    Args:
        - sol: solution list containing the genes.
            0. Number of LiIon batteries.
            1. Number of flywheel batteries.
            2. Number of supercapacitors.
    Returns: A value related to the total cost accumulated during simulation:
        100000/cost'''
    liion_cnt = sol[0]
    flywh_cnt = sol[1]
    sucap_cnt = sol[2]

    costs, metrics = objective(GreedySim, DF, liion_cnt, flywh_cnt, sucap_cnt)
    # cost = costs['total_costs']
    # cost = metrics['fluctuation']
    cost = metrics['peak_power_sum']
    print_gene_fitness(liion_cnt, flywh_cnt, sucap_cnt, cost)
    return 100000/cost

def on_generation(ga_instance: pygad.GA):
    sol, fit, _ = ga_instance.best_solution()
    print(f'sol: {sol}, fitness value: {fit}')

def optimize(config):
    ga_instance = pygad.GA(**config)
    ga_instance.run()

    sol, sol_fitness, _ = ga_instance.best_solution()
    print(f'Solution: {sol}')
    print(f'Fitness: {sol_fitness}')

def parse_config() -> dict:
    parser = argparse.ArgumentParser(description='Run genetic algorithm to optimize' +
                                     ' peak-shave.')
    parser.add_argument('--experiment', type=str, default='const',
                        help=('Determines the experiment to run. Possible values '
                              'are: `const`, `dyn`, `equalize`, `greedy`.'))
    parser.add_argument('--num_generations', type=int, default=500,
                        help='Number of generations in the genetic algorithm.')
    parser.add_argument('--sol_per_pop', type=int, default=10,
                        help='Number of solutions per population.')
    parser.add_argument('--datafile', type=str, default='Sub71125.csv',
                        help='Name of the file used as source data. File has to ' +
                        'be in the data folder.')
    parser.add_argument('--penalize_charging', action=argparse.BooleanOptionalAction,
                        default=False)
    args = parser.parse_args()

    if args.experiment not in {'const', 'dyn', 'equalize', 'greedy'}:
        raise Exception('--experiment must be either `const`, `dyn`, `equalize`, or `greedy`!')

    run_config = {
        'datafile': args.datafile,
        'penalize_charging': args.penalize_charging,
        'experiment': args.experiment,
    }

    pygad_config = {
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
        'mutation_num_genes': 1
    }

    configs = {
        'run_config': run_config,
        'pygad_config': pygad_config
    }
    return configs

def set_global_dataframe(fname: str) -> None:
    global DF
    print(f'Set dataframe from file: {fname}')
    DF = process_file(fname)

def main(configs):
    run_config = configs['run_config']
    pygad_config = configs['pygad_config']

    num_genes = 3
    gene_type = [int, int, int]
    gene_space = [{'low': 0, 'high': 5},
                  {'low': 0, 'high': 5},
                  {'low': 0, 'high': 5}]

    if run_config['experiment'] in {'const', 'dyn'}:
        num_genes += 1
        gene_type += [float]
        gene_space += [{'low': 0, 'high': .2}]

    if run_config['experiment'] == 'const':
        pygad_config['fitness_func'] = fitness_const
    elif run_config['experiment'] == 'dyn':
        pygad_config['fitness_func'] = fitness_dyn
    elif run_config['experiment'] == 'equalize':
        pygad_config['fitness_func'] = fitness_eq
    elif run_config['experiment'] == 'greedy':
        pygad_config['fitness_func'] = fitness_greedy
    
    pygad_config['num_genes'] = num_genes
    pygad_config['gene_type'] = gene_type
    pygad_config['gene_space'] = gene_space
    optimize(pygad_config)

if __name__ == '__main__':
    configs = parse_config()
    set_global_dataframe('../data/' + configs['run_config']['datafile'])
    main(configs)
