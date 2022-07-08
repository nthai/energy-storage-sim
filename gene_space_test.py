import pygad

def fitness(a, b):
    return 0

def main():
    config = {
        'fitness_func': fitness,
        'num_generations': 100,
        'num_parents_mating': 8,
        'sol_per_pop': 10,
        'num_genes': 4,
        'init_range_low': 0,
        'init_range_high': 1,
        'parent_selection_type': 'sss',
        'keep_parents': 2,
        'crossover_type': 'single_point',
        'mutation_type': 'random',
        'mutation_percent_genes': 50,
        'gene_type': [int, int, int, float],
        'gene_space': [{'low': 0, 'high': 50},
                       {'low': 0, 'high': 50},
                    #    [4, 8, 16, 20, 24],
                       list(range(4, 25, 4)),
                       {'low': 0, 'high': 1}]
    }

    ga_instance = pygad.GA(**config)
    ga_instance.run()

    print(ga_instance.initial_population)
    print(ga_instance.population)

if __name__ == '__main__':
    main()
