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

Use Python 3 and supply a Glucose 4.2.1 executable. Run from the repository root. If the executable is named `glucose` and is on `PATH`, you can omit `--solver`.

```powershell
python main.py instances/satisfiable.json --solver C:\path\to\glucose-simp.exe
python main.py instances/unsatisfiable.json --solver C:\path\to\glucose-simp.exe
python main.py instances/incomplete.json --solver C:\path\to\glucose-simp.exe --dimacs instance.cnf --stats
```

For SAT, the program prints each pair and any unmatched agents. For UNSAT, it prints `No stable matching exists.` The program sends CNF directly to Glucose through standard input. The `--dimacs` option saves a copy, and `--stats` prints Glucose's comment lines and measured wall time. The satisfiable example's CNF begins with `p cnf 4 8`. Input and solver errors go to stderr with exit code 2.


## Included examples

- `instances/satisfiable.json`: four agents with a stable pairing.
- `instances/unsatisfiable.json`: a three-agent preference cycle with no stable pairing.
- `instances/incomplete.json`: one acceptable pair and one isolated agent.

## Benchmark experiment

Run the reproducible search with your Glucose executable:

```powershell
python check_benchmark.py
python benchmark.py --solver C:\path\to\glucose-simp.exe
```

The benchmark generates complete mutual preference lists for 20, 40, 80, and 120 agents, using seeds 0 through 4 at each size. It prints CSV rows with the number of variables and clauses, Python encoding time (clauses plus DIMACS text), Glucose wall time, and SAT/UNSAT status. Each Glucose call has a 45-second timeout. The search stops at the first SAT case taking at least 10 seconds. `--save-hard path.json` optionally saves that case.

I ran this search with Python 3.14.3 and Glucose 4.2.1:

| Agents | Seeds tried | Variables | Clauses | SAT / UNSAT | Encoding time | Glucose wall time |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 20 | 0–4 | 190 | 3,610 | 4 / 1 | 0.003507–0.006435 s | 0.024069–0.309984 s |
| 40 | 0–4 | 780 | 30,420 | 4 / 1 | 0.031536–0.048185 s | 0.082217–0.117414 s |
| 80 | 0–4 | 3,160 | 249,640 | 2 / 3 | 0.289471–0.902647 s | 1.464496–1.699169 s |
| 120 | 0 | 7,140 | 849,660 | 1 / 0 | 2.619039 s | 22.983321 s |

The qualifying SAT case is `generate(120, 1.0, 0)` in `benchmark.py`. No large JSON file is included. Times vary by machine and load.

<!-- Documentation updated: 2026-11-23 16:20 -->
