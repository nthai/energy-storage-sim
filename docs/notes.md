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
* Fluctuation: $\frac{\sum{|p_i - p_{i - 1}|}}{\bar{p}}$, the sum of changes in power divided by the mean power.
* Periodic fluctuation: We compute the fluctuation for each day and take the average of it.
* Sum of peaks above the upper limit. Here we have to be careful with setting the upper limit, as a low sum could also be achieved by setting a very high upper limit.
* Count of peaks above the upper limit.
* Sum of bought electricity above the upper limit.
* Maximum electricity bought.

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
  * We use predicted data of the next 24 hours and use binary search to find the upper and lower limit. Constraints are:
    * `abs(upper - lower) = margin`, where the input parameter `margin` is a ratio of the distance between the max and min.
    * `abs(area_upper - area_lower) < tolerance`, where `tolerance` is an input parameter, `area_upper` is the approximation of the area above the upper limit and `area_lower` is the approximation of the area below the lower limit.
  * There is a possibility to multiply the lower limit by th input parameter `factor`. 
  
![equalized limits](figures/EqualizedLimPeakShaveSim.png)

* Greedy algorithm
  * The basic principle of the greedy algorithm is that if the electricity is cheap, we should buy as much as we can to charge our batteries and use the batteries when electricity is more expensive.
  * The algorithm computes how long the batteries would last and then looks that far into the future to see if there would be cheaper electricity prices later. If there is a future cheaper price, we wait until then, otherwise, we buy electricity to charge our batteries.

![greedy sim](figures/GreedySim.png)

# Results

## Results with constant limits

| Li-ion | Flywheel | Supercapacitor | Margin |    Cost   | Fluctuation | Mean fluctuation | Peak sum | Peak count |
|--------|----------|----------------|--------|-----------|-------------|------------------|----------|------------|
|   0    |     0    |        0       | 0.02   | 209902.85 |   466.50    |       2.22       |  3979.86 |    205     |
|   1    |     0    |        1       | 0.1833 | 221688.12 |   375.44    |       1.72       |  1879.41 |    118     |
|   1    |     0    |        1       | 0.0727 | 226413.79 |   321.79    |       1.49       |  2650.39 |    122     |
|   1    |     2    |        0       | 0.0810 | 229725.98 |   366.62    |       1.75       |  2447.16 |    112     |

## Results with dynamic limits

| Li-ion | Flywheel | Supercapacitor | Margin |    Cost   | Fluctuation | Mean fluctuation | Peak sum | Peak count |
|--------|----------|----------------|--------|-----------|-------------|------------------|----------|------------|
|   0    |     0    |        0       | 0.05   | 209902.85 |   466.50    |       2.22       | 3462.94  |    234     |
|   1    |     0    |        1       | 0.1918 | 216242.35 |   381.65    |       1.78       |  825.56  |    114     |
|   1    |     0    |        3       | 0.1088 | 223111.70 |   282.96    |       1.31       | 1281.14  |    131     |
|   1    |     1    |        1       | 0.0672 | 222051.81 |   218.78    |       1.02       | 1529.34  |    133     |

## Results with equalized limits

| Li-ion | Flywheel | Supercapacitor |    Cost   | Fluctuation | Mean fluctuation | Peak sum | Peak count |
|--------|----------|----------------|-----------|-------------|------------------|----------|------------|
|   0    |     0    |        0       | 209902.85 |    466.50   |       2.22       |  1820.35 |    227     |
|   0    |     0    |        1       | 213155.99 |    361.29   |       1.70       |   956.76 |    168     |
|   1    |     1    |        0       | 217192.79 |    337.46   |       1.59       |   299.18 |     69     |

## Results with greedy algorithm

| Li-ion | Flywheel | Supercapacitor |    Cost   | Fluctuation | Mean fluctuation |
|--------|----------|----------------|-----------|-------------|------------------|
|   0    |     0    |        0       | 209902.85 |    891.00   |       4.36       |
|   0    |     0    |        1       |  54135.20 |   8750.25   |      38.99       |
|   0    |     2    |        0       |  78939.61 |   9556.09   |      43.92       |
|   0    |     1    |        0       |  47259.91 |   8982.44   |      41.38       |

# Some thoughts

* After a certain capacity, the number of batteries do not matter anymore. The deciding factor of the performance measures is the margin, the (half-)distance between the upper and the lower limits.
* The self-discharge rate is an important factor. If we use supercapacitors, our performance measures degrade, because the supercapacitors lose a lot of charge between decisions compared to the Li-Ion battery. Note: this is also cause by the algorithm we implemented, because right now, supercapacitors have higher priority when charging.
* On this timescale the maximum rate of charge does not matter, as all types of batteries can be charged to full charge in an hour. (This is why we cannot use the benefits of a cupercapacitor to our advantage at the moment.)

# Questions
* How much energy is lost by using storages?