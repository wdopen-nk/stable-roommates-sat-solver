# Stable Roommates SAT Solver

This Python 3 program decides whether a stable roommates matching exists and prints one when it does. It asks whether a group of agents can be paired without a *blocking pair*: two agents who both prefer each other to their assigned partners. Preference lists are strict, can be incomplete, and must be mutually acceptable. A stable matching need not exist. The program turns the question into Boolean satisfiability (SAT), writes the formula in DIMACS CNF, runs an external Glucose 4.2.1 executable, and translates a satisfying assignment into pairs.

## Input format

Save one UTF-8 JSON object. Each key is an agent name, and its value is an ordered list of acceptable partners:

```json
{
  "A": ["B"],
  "B": ["A"],
  "C": []
}
```

Names must be unique nonempty strings. A list cannot contain an unknown agent, the agent themself, or the same partner twice. Acceptability must be mutual: if A lists B, B must list A. Empty lists are allowed.

## Current version

From the repository root, use Python 3:

```powershell
python main.py instances/satisfiable.json
python main.py instances/satisfiable.json --dimacs instance.cnf
```

Without `--dimacs`, `main.py` prints DIMACS to the terminal. With `--dimacs`, it saves an ASCII CNF file and prints its variable and clause counts. The first line of the small satisfiable example is `p cnf 4 8`.

## Included examples

- `instances/satisfiable.json`: four agents with a stable pairing.
- `instances/unsatisfiable.json`: a three-agent preference cycle with no stable pairing.
- `instances/incomplete.json`: one acceptable pair and one isolated agent.

<!-- Documentation updated: 2026-11-13 16:03 -->
