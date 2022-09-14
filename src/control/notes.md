# Notes for RL
## EhubEnv
### Questions
1. What is the state space?
2. What is the action space?
3. What should be the objective/reward?

### Action Space
$`\Delta SOC`$, the amount of value we want to charge/discharge the batteries with. In case of charge, we buy ectra power from the grid. In case of discharge, we use the power from the battery. If we charge or discharge too much, the energy will got to waste.

For later: it could be possible to decide which type of storage we would want to charge. E.g. a `(-.2, .5, .2)` action would mean that we discharge the Li-ion storage with 20 kW, and charge a flywheel and a supercapacitor with 50 kW and 20 kW respectively.

### Reward

We want to operate transformers close to 100% to minimize relative loss.
* Idea: try to operate the transformer close to 90%. The cost signal should represent how far we are from the 90%. If the power at the transformer (the power we take from the grid) exceeds the 100%, the cost should be even higher.

* Given a current load (`trafo_load`) and a nominal power (`trafo_nompower`), what should be used for distance metrics?

* The current reward used is
```math
r(t) = \begin{cases}
-(p(t) - pnom)^2 & \text{if $p(t) \leq pmax$} \\
-(p(t) - pnom)^2 - (pmax - p(t))^2 & \text{if $p(t) > pmax$}
\end{cases}
```
where $`p(t)`$ is the current load on the trafo, $`pnom`$ is the nominal power of the trafo (set to 90 kW by default), and $`pmax`$ is the maximum power of the trafo (set to 100 kW by default).

### State space

State space should include the following:
* timestamp
* state of charge (of each battery type, if we can charge them separately)
* net load in the previous timesteps
* in previous simulations it also contained the power produced by solar cells and the price of the electricity

### The `step()` function

Let $`a(t)`$ be the action taken at time $`t`$. At the $`t`$th timestep, the net load measurement provides information for the period in $`[t-1, t]`$. To calculate the reward for this timestep, that is, $`r(t)`$, we have to look at the action taken in the previous timestep, $`a(t-1)`$.

1. Look at action $`a(t-1)`$ and compute $`SOC(t)`$, the state-of-charge at time $`t`$.
2. In case of charging, add the power bought to the net load. In case of discharging, subtract the gained power from the net load. Note, that these powers do not equal the $`\Delta SOC`$, becuase the charging and discharging efficiencies are not 100%.
3. The computed power tells us how much power goes through the trafo. Compute the distance of the power from the trafo's nominal power.
4. $`r(t)`$ depends on the distance from the nominal power. If the power is closer to the nominal power, the reward should also be higher. However, if we exceed the maximum power of the trafe, we shuold punish the agent harshly.

## Frameworks
### stable baselines3

We must implement the gym interface. This means the following functions:
* `__init__(self)`: return None
* `reset(self)`: must return an observation as a numpy array
* `step(self, action)`: must return a tuple (observation, reward, done, info)
* `render(self, mode)`: not necessary
* `close(self)` not necessary

### rllib (ray)

A gym interface has to be implemented here too. Action mask can be implemented by overriding the algorithm and the policy itself (e.g.: https://github.com/ray-project/ray/blob/master/rllib/examples/random_parametric_agent.py or https://docs.ray.io/en/latest/rllib/rllib-models.html#variable-length-parametric-action-spaces)

## Other notes

Run with `python -m src.control.ehub_env` from the `src` directory.