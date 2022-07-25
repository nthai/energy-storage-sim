# Problem description
* Transformers provide a connection point grom the user to the electric grid.
* We want to deploy energy hubs to transformers.
* Energy hubs consist of multiple batteries.
* There are many kinds of batteries (Li-ion battery, flywheel, supercapacitor).
* We can control the charge of the batteries by deciding whether to charge or discharge a battery with given power, each hour.
* The capacity of a battery is set to be 100 kWh. We assume that each battery can be charged or discharged in an hour.
* Charging and discharging have efficiencies, that is, energy is lost due to heat. We also assume that there is a self-discharge rate, that is, some percentage of the stored energy is lost every hour.
* We want to find the optimal number of batteries in a given transformer.
* Dataset contains the net load (`power consumed - power produced`) with timestamp. Data is hourly.
* We assume that the dataset also contains price data.
* Peak-shaving problem. We are aiming to _shave off_ the peaks of the bought energy. That is, we want to use the stored energy when the net load would be high.

# Metrics and Objectives
* Total cost
  * Operational cost
  * Capital cost
  * Cost of electricity
  * Penalty for charging
* Fluctuation
* Periodic fluctuation: We compute the fluctuation for each day and take the average of it.
* Sum of peaks above the upper limit
* Count of peaks above the upper limit

# Algorithms
* Constant limits:
  * If the net demand is below the lower limit, we buy electricity to charge our batteries. If it is above the upper limit, we use batteries if we can.
  * The upper and the lower limits are set beforehand, based on historical data. We take a one year long time series data for the net power load demand. We compute the median and then set the upper and lower limit with a margin between them:
    * `upper = data.median() * (1 + margin)`
    * `lower = data.median() * (1 - margin)`

![constant limits](figures/ConstLimPeakShaveSim.png)

* Dynamic limits based on the median of future values
  * Similar to the previous case, but limits change dynamically.
  * We try to predict the net load for the next 24 hours, and compute its median and calculate the upper and lower limits with a margin:
    * `upper[t] = data[t:t+24].median() * (1 + margin)`
    * `lower[t] = data[t:t+24].median() * (1 - margin)`

![dynamic limits](figures/DynamicLimPeakShaveSim.png)

* Dynamic limits that equalizes the area above and below the upper and lower limits
  * 
  
![equalized limits](figures/EqualizedLimPeakShaveSim.png)

* Greedy algorithm

![greedy sim](figures/GreedySim.png)
