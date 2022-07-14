#!/bin/bash

# run single
python -O peak_shave_sim.py --liion 10 --flywheel 0 --supercap 0 --datafile Sub71125.csv

# run genetic algorithm
# python -O peak_shave_genopt.py --limit_mode dyn --num_generations 2 --datafile Sub71125.csv