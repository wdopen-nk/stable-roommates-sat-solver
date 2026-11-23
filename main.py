import argparse
import json
import subprocess
import sys
import time

class InstanceError(ValueError):
    """The input is not a valid instance."""


class SolverError(RuntimeError):
    """Glucose did not provide a valid result."""


def unique_pairs(ps):
    """Build a dictionary and reject repeated JSON names."""
    result = {}

    for name, value in ps:
        if name in result:
            raise InstanceError(f"duplicate agent name: {name!r}")

        result[name] = value

    return result


def validate_preferences(data):
    """Check that preference lists are strict and acceptability is mutual."""
    if not isinstance(data, dict):
        raise InstanceError("the JSON root must map agent names to preference lists")

    if not data:
        raise InstanceError("at least one agent is required")

    for name in data:
        if not isinstance(name, str) or not name.strip():
            raise InstanceError("agent names must be nonempty strings")

    for name, ranked in data.items():
        if not isinstance(ranked, list):
            raise InstanceError(f"{name!r} must have a list of partners")

        seen = set()
        for partner in ranked:
            if not isinstance(partner, str):
                raise InstanceError(f"{name!r} has a non-string partner")

            if partner == name:
                raise InstanceError(f"{name!r} ranks themself")

            if partner not in data:
                raise InstanceError(f"{name!r} ranks unknown agent {partner!r}")

            if partner in seen:
                raise InstanceError(f"{name!r} ranks a partner more than once")

            seen.add(partner)

    # If A lists B, B must list A too.
    for name, ranked in data.items():
        for partner in ranked:
            if name not in data[partner]:
                raise InstanceError(f"acceptability is not mutual: {name!r}, {partner!r}")

    return data


def load_preferences(path):
    """Read one UTF-8 JSON file and validate it."""
    try:
        with open(path, encoding="utf-8") as source:
            data = json.load(source, object_pairs_hook=unique_pairs)

    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise InstanceError(f"cannot read {path}: {error}")

    return validate_preferences(data)


def encode(preferences):
    """Give each acceptable pair a number and build the CNF clauses."""
    pairs = []

    for first in sorted(preferences):
        for second in sorted(preferences[first]):
            if first < second:  # (A, B) and (B, A) are the same pair.
                pairs.append((first, second))

    numbers = {}

    for number, pair in enumerate(pairs, 1):
        numbers[pair] = number

    def variable(first, second):
        if first > second:
            first, second = second, first

        return numbers[(first, second)]

    clauses = []

    # An agent cannot belong to two selected pairs.
    for name, ranked in preferences.items():
        incident = [variable(name, other) for other in ranked]

        for i in range(len(incident)):
            for j in range(i + 1, len(incident)):
                clauses.append([-incident[i], -incident[j]])

    # A pair must be selected unless one endpoint has a preferred partner.
    for first, second in pairs:
        clause = [variable(first, second)]

        for other in preferences[first]:
            if other == second:
                break

            clause.append(variable(first, other))

        for other in preferences[second]:
            if other == first:
                break

            clause.append(variable(second, other))

        clauses.append(clause)

    return pairs, clauses


def dimacs(pairs, clauses):
    """Format the clauses as a DIMACS CNF file."""
    lines = [f"p cnf {len(pairs)} {len(clauses)}"]

    for clause in clauses:
        lines.append(" ".join(str(number) for number in clause) + " 0")

    return "\n".join(lines) + "\n"


def decode(pairs, true_variables):
    """Turn true pair variables back into agent pairs."""
    chosen_pairs = []

    for number, pair in enumerate(pairs, 1):
        if number in true_variables:
            chosen_pairs.append(pair)

    return chosen_pairs


def is_stable(preferences, chosen_pairs):
    """Check the matching directly against the original rankings."""
    partner_of = {}

    for first, second in chosen_pairs:
        if (first not in preferences or second not in preferences[first] or
                first in partner_of or second in partner_of):
            return False

        partner_of[first] = second
        partner_of[second] = first

    for first, ranked in preferences.items():
        for second in ranked:
            if first >= second or partner_of.get(first) == second:
                continue

            first_partner = partner_of.get(first)
            second_partner = partner_of.get(second)

            first_wants = first_partner is None or ranked.index(second) < ranked.index(first_partner)
            second_wants = (second_partner is None or
                            preferences[second].index(first) < preferences[second].index(second_partner))

            if first_wants and second_wants:
                return False

    return True


def parse_output(output, returncode, variable_count, clauses):
    """Read and check Glucose's status, model, and comment lines."""
    statuses = []
    literals = []
    statistics = []

    for line in output.splitlines():
        parts = line.split()

        if not parts:
            continue

        if parts[0] == "s":
            statuses.append(" ".join(parts[1:]))

        elif parts[0] == "v":
            try:
                literals.extend(int(part) for part in parts[1:])

            except ValueError:
                raise SolverError("Glucose returned an invalid model literal")

        elif parts[0] == "c":
            statistics.append(line.strip())

    if len(statuses) != 1 or statuses[0] not in ("SATISFIABLE", "UNSATISFIABLE"):
        raise SolverError("Glucose did not return one valid SAT/UNSAT status")

    satisfiable = statuses[0] == "SATISFIABLE"
    expected_code = 10 if satisfiable else 20

    if returncode not in (0, expected_code):
        raise SolverError(f"Glucose returned exit code {returncode} for {statuses[0]}")

    if not satisfiable:
        if literals:
            raise SolverError("Glucose returned a model with UNSAT")
        return False, set(), statistics

    if variable_count and (not literals or literals[-1] != 0):
        raise SolverError("Glucose returned an unterminated model")

    assignments = {}

    for literal in literals:
        if literal == 0:  # Zero ends a DIMACS model line.
            continue

        number = abs(literal)

        if number < 1 or number > variable_count:
            raise SolverError(f"Glucose returned out-of-range variable {number}")

        value = literal > 0

        if number in assignments and assignments[number] != value:
            raise SolverError(f"Glucose returned conflicting values for variable {number}")

        assignments[number] = value

    if len(assignments) != variable_count:
        raise SolverError("Glucose returned an incomplete model")

    for clause in clauses:
        if not any(assignments[abs(literal)] == (literal > 0) for literal in clause):
            raise SolverError("Glucose returned a model that does not satisfy the CNF")

    true_variables = {number for number, value in assignments.items() if value}

    return True, true_variables, statistics


def run_glucose(pairs, clauses, executable="glucose", timeout=None, formula=None):
    """Send DIMACS to Glucose and check its answer."""
    if formula is None:
        formula = dimacs(pairs, clauses)

    start = time.perf_counter()

    try:
        completed = subprocess.run(
            [executable, "-model"],
            input=formula, capture_output=True,
            text=True, errors="replace", timeout=timeout,
        )

    except FileNotFoundError:
        raise SolverError(f"Glucose executable not found: {executable}")

    except (OSError, subprocess.TimeoutExpired) as error:
        raise SolverError(f"Glucose could not complete: {error}")

    elapsed = time.perf_counter() - start

    try:
        satisfiable, true_variables, statistics = parse_output(
            completed.stdout, completed.returncode, len(pairs), clauses
        )

    except SolverError as error:
        detail = completed.stderr.strip()
        raise SolverError(f"{error}; stderr: {detail}" if detail else str(error))

    return satisfiable, true_variables, statistics, elapsed


def main(argv=None):
    parser = argparse.ArgumentParser(description="Solve Stable Roommates with Glucose 4.2.1")

    parser.add_argument("instance", help="JSON preference file")
    parser.add_argument("--dimacs", help="save the DIMACS formula to a file")
    parser.add_argument("--solver", default="glucose", help="Glucose executable or path")
    parser.add_argument("--stats", action="store_true", help="print Glucose statistics")

    args = parser.parse_args(argv)

    try:
        preferences = load_preferences(args.instance)
        pairs, clauses = encode(preferences)
        formula = dimacs(pairs, clauses)

        if args.dimacs:
            with open(args.dimacs, "w", encoding="ascii", newline="\n") as output:
                output.write(formula)

        satisfiable, true_variables, statistics, elapsed = run_glucose(
            pairs, clauses, args.solver, formula=formula
        )

        if satisfiable:
            chosen_pairs = decode(pairs, true_variables)

            if not is_stable(preferences, chosen_pairs):
                raise SolverError("decoded matching is not stable")

            print("Stable matching found:")

            for first, second in chosen_pairs:
                print(f"  {first} - {second}")

            matched = {name for pair in chosen_pairs for name in pair}
            unmatched = sorted(set(preferences) - matched)

            print("Unmatched: " + (", ".join(unmatched) if unmatched else "none"))

        else:
            print("No stable matching exists.")

        if args.stats:
            print(f"Glucose wall time: {elapsed:.3f} s")

            for line in statistics:
                print(line)

    except (InstanceError, SolverError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
