"""Day-by-day commuter simulation on the Braess network.

Network: Westbury (W) -> Eastfield (E), two ways round a lake.
  north route: W->N narrow road (time grows with traffic), N->E motorway (fixed)
  south route: W->S motorway (fixed), S->E narrow road (time grows with traffic)
  bridge:      N->S, takes no time at all (only in some experiments)

Each morning every driver independently re-plans with probability `switch`.
A perfect driver (noise 0) moves to the fastest route with a chance that grows with the time it saves; a noisy driver picks by logit choice from yesterday's times. The fastest
one, or with `noise` > 0 a logit choice (higher noise = worse at judging routes).
"""

from dataclasses import dataclass
import json
import sys

import numpy as np

NARROW_MIN_PER_CAR = 1 / 100
MOTORWAY_MIN = 45.0
GAIN_FOR_FULL_SWITCH = 5.0  # minutes saved at which a re-planning driver always switches

ROUTES = {
    "north": ("WN", "NE"),
    "south": ("WS", "SE"),
    "bridge": ("WN", "NS", "SE"),
}


@dataclass(frozen=True)
class Experiment:
    name: str
    drivers: int = 4000
    days: int = 60
    bridge: bool = False
    switch: float = 0.1
    noise: float = 0.0
    seed: int = 0
    start_from: tuple = ()  # optional initial route index per driver
    toll: float = 0.0  # bridge toll, in minutes a driver would pay to avoid; changes choices, not trip times


def link_times(counts: dict[str, int]) -> dict[str, float]:
    on = lambda *routes: sum(counts.get(r, 0) for r in routes)
    return {
        "WN": on("north", "bridge") * NARROW_MIN_PER_CAR,
        "SE": on("south", "bridge") * NARROW_MIN_PER_CAR,
        "NE": MOTORWAY_MIN,
        "WS": MOTORWAY_MIN,
        "NS": 0.0,
    }


def route_times(counts: dict[str, int]) -> dict[str, float]:
    links = link_times(counts)
    return {r: sum(links[l] for l in legs) for r, legs in ROUTES.items()}


def run(exp: Experiment) -> dict:
    rng = np.random.default_rng(exp.seed)
    names = [r for r in ROUTES if exp.bridge or r != "bridge"]
    choice = np.array(exp.start_from) if len(exp.start_from) else rng.integers(0, 2, exp.drivers)
    history = []
    for day in range(exp.days):
        counts = {r: int((choice == i).sum()) for i, r in enumerate(names)}
        times = route_times(counts)
        avg = sum(counts[r] * times[r] for r in names) / exp.drivers
        history.append({"day": day, "counts": counts,
                        "times": {r: round(times[r], 2) for r in names},
                        "avg": round(avg, 2)})
        t = np.array([times[r] + (exp.toll if r == "bridge" else 0.0) for r in names])  # what drivers weigh
        if exp.noise > 0:
            w = np.exp(-(t - t.min()) / exp.noise)
            p = w / w.sum()
            replan = rng.random(exp.drivers) < exp.switch
            choice[replan] = rng.choice(len(names), replan.sum(), p=p)
        else:
            # A driver moves to the fastest route with a chance that grows with the minutes saved,
            # so near a tie only a few switch and the crowd settles instead of sloshing back and forth.
            gain = t[choice] - t.min()
            moves = rng.random(exp.drivers) < exp.switch * np.minimum(1.0, gain / GAIN_FOR_FULL_SWITCH)
            best = np.flatnonzero(t == t.min())
            choice[moves] = rng.choice(best, moves.sum())
    return {"experiment": {k: v for k, v in exp.__dict__.items() if k != "start_from"},
            "history": history, "final_choice": choice.tolist()}


def settled_avg(result: dict, last: int = 10) -> float:
    return float(np.mean([h["avg"] for h in result["history"][-last:]]))


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "results.json"
    runs = []
    for seed in range(5):
        runs.append(run(Experiment("no_bridge", seed=seed)))
        runs.append(run(Experiment("bridge", bridge=True, seed=seed)))
    for noise in [0.0, 2.0, 5.0, 10.0, 20.0, 40.0, 1e9]:
        for seed in range(5):
            runs.append(run(Experiment(f"bridge_noise_{noise:g}", bridge=True, noise=noise, seed=seed)))
    for drivers in [1000, 2000, 3000, 4000, 4500, 5000, 6000]:
        for bridge in [False, True]:
            runs.append(run(Experiment(f"demand_{drivers}_{'bridge' if bridge else 'none'}",
                                       drivers=drivers, bridge=bridge)))
    for seed in range(5):
        smart = run(Experiment("twist_phase1_smart", bridge=True, seed=seed))
        runs.append(smart)
        runs.append(run(Experiment("twist_phase2_guessing", bridge=True, noise=1e9, days=30, seed=seed,
                                   start_from=tuple(smart["final_choice"]))))
    for drivers in [4500, 5000, 6000]:
        for seed in range(5):
            r = run(Experiment(f"demand_{drivers}_bridge_long", drivers=drivers, bridge=True, days=200, seed=seed))
            runs.append(r)
    for toll in [0, 5, 10, 15, 20, 22.5, 25, 30]:
        for seed in range(5):
            runs.append(run(Experiment(f"toll_{toll:g}", bridge=True, toll=toll, days=120, seed=seed)))
    for seed in range(5):
        smart = run(Experiment("relapse_phase1_smart", bridge=True, seed=seed))
        guess = run(Experiment("relapse_phase2_guessing", bridge=True, noise=1e9, days=30, seed=seed,
                               start_from=tuple(smart["final_choice"])))
        runs.append(run(Experiment("relapse_phase3_smart_again", bridge=True, days=60, seed=seed,
                                   start_from=tuple(guess["final_choice"]))))
    for seed in range(5):
        before = run(Experiment("close_phase1_bridge", bridge=True, days=100, seed=seed))
        runs.append(before)
        rng = np.random.default_rng(seed + 100)
        choice = np.array(before["final_choice"])
        on_bridge = choice == 2  # bridge is gone: its users fall back on north or south at random
        choice[on_bridge] = rng.integers(0, 2, on_bridge.sum())
        runs.append(run(Experiment("close_phase2_removed", bridge=False, days=30, seed=seed,
                                   start_from=tuple(choice))))
    for seed, north_share in enumerate([0.9, 0.15, 0.75, 0.3, 0.95]):
        start = (np.random.default_rng(seed).random(4000) >= north_share).astype(int)  # 0 north, 1 south
        runs.append(run(Experiment(f"scattered_start_{north_share:g}", seed=seed, days=30, start_from=tuple(start))))
    for r in runs:
        r.pop("final_choice", None)
    json.dump(runs, open(out, "w"))
    summary: dict[str, list[float]] = {}
    for r in runs:
        summary.setdefault(r["experiment"]["name"], []).append(settled_avg(r))
    for name, vals in summary.items():
        print(f"{name:28s} settled avg {np.mean(vals):6.2f} min  (seeds {len(vals)}, spread {np.ptp(vals):.2f})")
