# Notes for RL
## EhubEnv
### Questions
1. What is the state space?
2. What is the action space?
3. What should be the objective/reward?

### Action Space
$\Delta SOC$, the amount of value we want to charge/discharge the batteries with. In case of charge, we buy ectra power from the grid. In case of discharge, we use the power from the battery. If we charge or discharge too much, the energy will got to waste.

For later: it could be possible to decide which type of storage we would want to charge. E.g. a `(-.2, .5, .2)` action would mean that we discharge the Li-ion storage with 20 kW, and charge a flywheel and a supercapacitor with 50 kW and 20 kW respectively.

### Reward

We want to operate transformers close to 100% to minimize relative loss.
* Idea: try to operate the transformer close to 90%. The cost signal should represent how far we are from the 90%. If the power at the transformer (the power we take from the grid) exceeds the 100%, the cost should be even higher.

## State space

State space should include the following:
* state of charge (of each battery type, if we can charge them separately)
* net load in the previous timesteps