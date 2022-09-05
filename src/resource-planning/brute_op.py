import pandas as pd
from scipy.optimize import brute
from objective import objective

DF = pd.read_csv('../data/full.csv')
def fitness(sol):
    liion_cnt = sol[0]
    flywh_cnt = sol[1]
    sucap_cnt = sol[2]
    cost = objective(DF, float('inf'), liion_cnt, flywh_cnt, sucap_cnt)
    return cost

x0, fval, _, _ = brute(fitness, (slice(0, 50, 1), slice(0, 50, 1), slice(0, 50, 1)), disp=True, finish=None, full_output=True)

print(x0)
print(fval)
