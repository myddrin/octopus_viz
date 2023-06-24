# Octopus Viz

The current Octopus App (v3.71.2 on Android) does not allow visualisation:
- of monetary value when using the Flux tariff
- of visualising aggregated data for a longer period than 1 day at the half hour rate.

The goal of this project is to:
- create a cache of the electric consumption of a given system
- query said cache to map it to prices
  - to visualise the price of import for a period
  - to visualise the price of export per a period
  - to visualise the usage by half-hour aggregates over longer periods than 1 day

Octopus API documentation: https://developer.octopus.energy/docs/api

## Why a cache?

The Octopus API allows the gathering of data at the half-hour precision with a maximum of 25,000 entries per page (`2 * 24 * 365 = 17,520` so more than enough to see 1 year of half-hour data).

By using a cache for that data we:
- do not need to use their API for the visualisation part
- do not risk to get rate-limited if querying multiple time (I'm not sure if any rate limitation applies)

So the cache is lower priority.

## Visualisation

The current Octopus App or website allow the visualisation of a day:

![original_consumption.PNG](original_consumption.PNG)

But this project should allow to have this view over longer periods of time than a day still accumulating at the half-hour interval.

## Note: Octopus Flux

Source: https://octopus.energy/smart/flux/

Is a tariff with 3 levels of price for import and export:
- 1 base price during most of the day, usually slightly lower than the national average.
- 1 low price at the early hours (02:00 to 05:00)
- 1 high price at the peak hours (16:00 to 19:00)
 
![flux_explainer.svg](flux_explainer.svg)
