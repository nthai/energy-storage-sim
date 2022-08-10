#!/bin/bash

# run single
# python -O peak_shave_sim.py

# run genetic algorithm

# python -O genetic_op.py \
#     --experiment const \
#     --num_generations 5 \
#     --sol_per_pop 8 \
#     --datafile Sub71125.csv \
#     --penalize_charging

# batch run
python -O genetic_op.py \
    --experiment const \
    --num_generations 30 \
    --sol_per_pop 8 \
    --datafile Sub71125.csv \
    --penalize_charging \
    > logs/peaksumopt_const.log &

python -O genetic_op.py \
    --experiment dyn \
    --num_generations 30 \
    --sol_per_pop 8 \
    --datafile Sub71125.csv \
    --penalize_charging \
    > logs/peaksumopt_dynamic.log &

python -O genetic_op.py \
    --experiment equalize \
    --num_generations 30 \
    --sol_per_pop 8 \
    --datafile Sub71125.csv \
    --penalize_charging \
    > logs/peaksumopt_equalized.log &

# python -O genetic_op.py \
#     --experiment greedy \
#     --num_generations 25 \
#     --sol_per_pop 8 \
#     --datafile Sub71125.csv \
#     --penalize_charging \
#     > logs/peaksumopt_greedy.log &
