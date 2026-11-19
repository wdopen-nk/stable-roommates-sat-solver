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

<!-- Documentation updated: 2026-11-19 11:25 -->
