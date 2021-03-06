#!/bin/bash

# run single
# python -O peak_shave_sim.py --liion 10 --flywheel 0 --supercap 0 --datafile Sub71125.csv

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
    --num_generations 500 \
    --sol_per_pop 8 \
    --datafile Sub71125.csv \
    --penalize_charging \
    > logs/const.log &

python -O genetic_op.py \
    --experiment dyn \
    --num_generations 500 \
    --sol_per_pop 8 \
    --datafile Sub71125.csv \
    --penalize_charging \
    > logs/dynamic.log &

python -O genetic_op.py \
    --experiment equalize \
    --num_generations 500 \
    --sol_per_pop 8 \
    --datafile Sub71125.csv \
    --penalize_charging \
    > logs/equalized.log &

python -O genetic_op.py \
    --experiment greedy \
    --num_generations 100 \
    --sol_per_pop 8 \
    --datafile Sub71125.csv \
    --penalize_charging \
    > logs/greedy.log &
