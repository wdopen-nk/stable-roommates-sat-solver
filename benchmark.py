import argparse
import json
import random
import sys
import time

from main import SolverError, decode, dimacs, encode, is_stable, run_glucose

SIZES = (20, 40, 80, 120, 130)
SEEDS = range(5)
DENSITY = 1.0
TARGET_SECONDS = 10.0
TIMEOUT_SECONDS = 45.0


def generate(size, density, seed):
    """Choose mutual acceptable pairs, then shuffle each ranking."""
    rng = random.Random(seed)
    names = [f"a{index:04d}" for index in range(size)]
    preferences = {name: [] for name in names}

    for index, first in enumerate(names):
        for second in names[index + 1:]:
            if rng.random() < density:
                preferences[first].append(second)
                preferences[second].append(first)

    for ranked in preferences.values():
        rng.shuffle(ranked)

    return preferences


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--solver", default="glucose", help="Glucose executable or path")
    parser.add_argument("--save-hard", help="save the first slow SAT instance as JSON")

    args = parser.parse_args(argv)

    print("size,seed,variables,clauses,encoding_seconds,solver_seconds,status", flush=True)

    for size in SIZES:
        for seed in SEEDS:
            preferences = generate(size, DENSITY, seed)
            start = time.perf_counter()
            pairs, clauses = encode(preferences)
            formula = dimacs(pairs, clauses)
            encoding_seconds = time.perf_counter() - start

            try:
                satisfiable, true_variables, _, solver_seconds = run_glucose(
                    pairs, clauses, args.solver, timeout=TIMEOUT_SECONDS, formula=formula
                )

            except SolverError as error:
                print(f"error: {error}", file=sys.stderr)
                return 2

            if satisfiable and not is_stable(preferences, decode(pairs, true_variables)):
                print("error: solver produced an unstable matching", file=sys.stderr)
                return 2

            status = "SAT" if satisfiable else "UNSAT"

            print(f"{size},{seed},{len(pairs)},{len(clauses)},"
                  f"{encoding_seconds:.6f},{solver_seconds:.6f},{status}", flush=True)

            if satisfiable and solver_seconds >= TARGET_SECONDS:
                if args.save_hard:
                    try:
                        with open(args.save_hard, "w", encoding="utf-8") as output:
                            json.dump(preferences, output, indent=2)
                            output.write("\n")

                    except OSError as error:
                        print(f"error: cannot save {args.save_hard}: {error}", file=sys.stderr)
                        return 2
                
                return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
