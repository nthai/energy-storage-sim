from distutils.command.config import config
import pygad
import pandas as pd

from objective import objective

class SimObj:
    def __init__(self, fname) -> None:
        self.df = pd.read_csv(fname)
    
    def fitness(self, sol, sol_idx):
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
    return 10000/cost

def main():
    obj = SimObj('../data/short.csv')
    config = {
        # 'fitness_func': obj.fitness,
        'fitness_func': fitness2,
        'num_generations': 100,
        'num_parents_mating': 4,
        'sol_per_pop': 8,
        'num_genes': 3,
        'init_range_low': 2,
        'init_range_high': 5,
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
