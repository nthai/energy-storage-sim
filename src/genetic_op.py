from functools import partial
import pygad
import pandas as pd

from objective import objective

class SimObj:
    def __init__(self, fname) -> None:
        self.df = pd.read_csv(fname)
    
    def __call__(self, sol, sol_idx):
        liion_cnt = sol[0]
        flywh_cnt = sol[1]
        sucap_cnt = sol[2]
        cost = objective(self.df, float('inf'), liion_cnt, flywh_cnt, sucap_cnt)
        return 10000/cost

DF = pd.read_csv('../data/full.csv')
def fitness2(sol, sol_idx):
    liion_cnt = sol[0]
    flywh_cnt = sol[1]
    sucap_cnt = sol[2]
    cost = objective(DF, float('inf'), liion_cnt, flywh_cnt, sucap_cnt)
    return 1000000/cost

def on_generation(ga_instance):
    sol, fit, _ = ga_instance.best_solution()
    print(f'sol: {sol}, fitness value: {fit}')

def main():
    obj = SimObj('../data/short.csv')

    df = pd.read_csv('../data/full.csv')

    config = {
        # 'fitness_func': obj,
        'fitness_func': fitness2,
        'on_generation': on_generation,
        'num_generations': 50,
        'num_parents_mating': 4,
        'sol_per_pop': 8,
        'num_genes': 3,
        'init_range_low': 0,
        'init_range_high': 50,
        'parent_selection_type': 'sss',
        'keep_parents': 1,
        'crossover_type': 'single_point',
        'mutation_type': 'random',
        'mutation_percent_genes': 10,
        'gene_type': int
    }

    ga_instance = pygad.GA(**config)
    ga_instance.run()

    sol, sol_fitness, sol_idx = ga_instance.best_solution()
    print(f'Solution: {sol}')
    print(f'Fitness: {sol_fitness}')

if __name__ == '__main__':
    main()
