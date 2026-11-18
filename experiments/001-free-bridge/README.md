# 001: The free bridge

4,000 drivers commute from Westbury to Eastfield every morning, around a lake.
Adding a free bridge that takes zero time to cross makes the average commute go from 65 minutes to 80.

This is the network from Dietrich Braess's 1968 paper. The drivers and their day-by-day behaviour are this simulation's own.

## The model

```
            narrow road               motorway
 Westbury ─────────────── North ─────────────── Eastfield
     │                      │ bridge (0 min)        │
     └─────────────────── South ────────────────────┘
            motorway                 narrow road
```

- A **narrow road** takes 1 minute per 100 cars on it.
- A **motorway** always takes 45 minutes.
- The **bridge**, when it exists, takes 0 minutes.
- An optional **toll** on the bridge is added to what drivers weigh, not to their trip time.
- Each morning, every driver re-plans with probability 10%. A perfect driver moves to yesterday's fastest route, with a chance that grows with the minutes it would save (full chance at 5 minutes). A noisy driver picks a route by logit choice, so small differences fool them more often than big ones.

## Results (5 random seeds each, average over the last 10 days)

| Experiment | Average commute |
|---|---|
| No bridge | 65.0 min |
| With the bridge | 79.9 min |
| Bridge, a little noise in judgement (noise 5) | 73.0 min |
| Bridge, a lot of noise (noise 20) | 67.6 min |
| Bridge, drivers pick routes at random | 65.5 min |
| Jammed town switched to guessing for 30 days | 66.1 min |
| Bridge removed on day 100 | 65.0 min the next day |

Town size changes everything:

| Drivers | No bridge | With bridge |
|---|---|---|
| 1,000 | 50 | 20 |
| 2,000 | 55 | 40 |
| 3,000 | 60 | 60 |
| 4,000 | 65 | 80 |
| 5,000 | 70 | 90 |
| 6,000 | 75 | 90 |

A toll on the bridge (counted in minutes; it changes choices, not trip times):

| Toll | Average commute | Drivers on the bridge |
|---|---|---|
| none | 80.0 min | 4,000 |
| 10 min | 72.5 min | 3,000 |
| 15 min | 67.5 min | 2,000 |
| 20 min | 65.0 min | 1,000 |
| 22.5 min | 64.7 min | 500 |
| 25 min or more | 65.0 min | 0 |

The best result is not removing the bridge: pricing it so about 500 drivers use it beats the town with no bridge.

These match the equilibria you can work out by hand: 45 + N/200 minutes without the bridge, and N/50 (capped at 90) with it.

## Run it

```bash
pip install -r requirements.txt
python braess.py results.json
```

It prints the settled average for every experiment and writes the full day-by-day history to `results.json`.

## References

- D. Braess, "Über ein Paradoxon aus der Verkehrsplanung", *Unternehmensforschung* 12, 258–268 (1968). English translation: D. Braess, A. Nagurney, T. Wakolbinger, "On a Paradox of Traffic Planning", *Transportation Science* 39(4) (2005).
- H. Youn, M. T. Gastner, H. Jeong, "Price of Anarchy in Transportation Networks: Efficiency and Optimality Control", *Physical Review Letters* 101, 128701 (2008).
