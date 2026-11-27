# Stable Roommates SAT Solver

This Python 3 program decides whether a stable roommates matching exists and prints one when it does. It asks whether a group of agents can be paired without a *blocking pair*: two agents who both prefer each other to their assigned partners. Preference lists are strict, can be incomplete, and must be mutually acceptable. A stable matching need not exist. The program turns the question into Boolean satisfiability (SAT), writes the formula in DIMACS CNF, runs an external Glucose 4.2.1 executable, and translates a satisfying assignment into pairs.

## Mathematical model and CNF encoding

Let `V` be the set of agents. Each agent `i` gives a strict ordered list `P(i)` of acceptable partners. If `j` is in `P(i)`, then `i` must be in `P(j)`. An unmatched agent prefers every acceptable partner to remaining unmatched. Let `E` contain each mutually acceptable unordered pair once.

A matching `M` is a subset of `E` in which each agent occurs in at most one pair. An acceptable pair `(i, j)` blocks `M` when it is not in `M` and both agents prefer each other to their current partners (or are unmatched). The problem is to decide whether a matching with no blocking pair exists and, if it does, output one.

The program creates one Boolean variable `x(i,j)` for each pair in `E`. It is true exactly when that pair is selected. For each agent `i` and each two distinct acceptable partners `j` and `k`, it adds a clause saying `NOT x(i,j) OR NOT x(i,k)`. This prevents an agent from being matched twice.

For every acceptable pair `(i,j)`, it also adds this stability clause:

```text
x(i,j)
OR x(i,k) for every k that i ranks above j
OR x(j,l) for every l that j ranks above i
```

If `(i,j)` is not selected, the clause requires at least one endpoint to have a partner they prefer. Thus `(i,j)` cannot block. There is no clause forcing every agent to have a partner: an unmatched agent is allowed when the matching is stable. Every satisfying assignment therefore describes a stable matching, and every stable matching satisfies the clauses. The program checks the returned assignment against both the CNF and the original rankings before printing it.

With `d(i)` acceptable partners for agent `i`, this encoding has `|E|` variables and `|E| + sum over i of d(i) * (d(i) - 1) / 2` clauses. The complete-list case grows cubically in the number of agents. One alternative is a sequential counter for the at-most-one constraint: it uses extra variables and roughly linear space per agent instead of all partner pairs. That can reduce large formulas, but makes the implementation and DIMACS mapping less direct. Requiring exactly one partner is another possible model for complete matchings, but would incorrectly reject valid stable matchings with unmatched agents here.

## User guide

### Input format

Save one UTF-8 JSON object. Each key is an agent name, and its value is an ordered list of acceptable partners:

```json
{
  "A": ["B"],
  "B": ["A"],
  "C": []
}
```

Names must be unique nonempty strings. A list cannot contain an unknown agent, the agent themself, or the same partner twice. Acceptability must be mutual: if A lists B, B must list A. Empty lists are allowed.

### How To Run

Use Python 3 and supply a Glucose 4.2.1 executable. Run from the repository root. If the executable is named `glucose` and is on `PATH`, you can omit `--solver`.

```powershell
python main.py instances/satisfiable.json --solver C:\path\to\glucose-simp.exe
python main.py instances/unsatisfiable.json --solver C:\path\to\glucose-simp.exe
python main.py instances/incomplete.json --solver C:\path\to\glucose-simp.exe --dimacs instance.cnf --stats
```

### Output

For a satisfiable instance, the script prints the pairs and any unmatched agents. For example, `instances/satisfiable.json` prints:

```text
Stable matching found:
  A - B
  C - D
Unmatched: none
```

The unsatisfiable example prints `No stable matching exists.` The incomplete example prints `A - B` and `Unmatched: C`. The program sends CNF directly to Glucose through standard input. The `--dimacs` option saves a copy, and `--stats` prints Glucose's comment lines and measured wall time. DIMACS starts with `p cnf <variables> <clauses>` where each following line is one clause using positive or negative variable numbers and ends in `0`. For example, the satisfiable instance starts with `p cnf 4 8`. Input and solver errors go to stderr with exit code 2.

## Included examples

- `instances/satisfiable.json`: four agents given where `(A,B)` and `(C,D)` form a stable matching.
- `instances/unsatisfiable.json`: three agents form a preference cycle. Any matching leaves one unmatched agent and has a blocking pair.
- `instances/incomplete.json`: `(A,B)` is the only acceptable pair; `C` is unmatched.

## Benchmark experiment

Run the reproducible search with your Glucose executable:

```
python benchmark.py --solver C:\path\to\glucose-simp.exe
```

The benchmark generates complete mutual preference lists for 20, 40, 80, and 120 agents, using seeds 0 through 4 at each size. It prints CSV rows with the number of variables and clauses, Python encoding time (clauses plus DIMACS text), Glucose wall time, and SAT/UNSAT status. Each Glucose call has a 45-second timeout. The search stops at the first SAT case taking at least 10 seconds. `--save-hard path.json` optionally saves that case.

I ran this search with Python 3.14.3 and Glucose 4.2.1:

| Agents | Seeds tried | Variables | Clauses | SAT / UNSAT | Encoding time | Glucose wall time |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 20 | 0–4 | 190 | 3,610 | 4 / 1 | 0.002315-0.003831 s | 0.024069–0.309984 s |
| 40 | 0–4 | 780 | 30,420 | 4 / 1 |  0.025463-0.029313 s | 0.082217–0.117414 s |
| 80 | 0–4 | 3,160 | 249,640 | 2 / 3 |  0.218970-0.252352 s | 1.193672-1.257597 s |
| 120 | 0-4 | 7,140 | 849,660 | 3 / 1 | 0.791831-0.869535 s | 8.238213-8.698314 s |
| 130 | 0 | 8,385 | 1,081,665 | 1 / 0 | 1.072217 s | 12.026799 s |

The qualifying SAT case is `generate(130, 1.0, 0)` in `benchmark.py`. Times vary by machine and load, and the result does not imply every 120-agent instance finishes in this time.

<!-- Documentation updated: 2026-11-27 23:44 -->
