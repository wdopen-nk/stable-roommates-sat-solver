import argparse
import json
import sys


class InstanceError(ValueError):
    """The input is not a valid instance."""

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
        raise InstanceError(f"cannot read {path}: {error}") from error
    
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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Encode Stable Roommates as DIMACS CNF")

    parser.add_argument("instance", help="JSON preference file")
    parser.add_argument("--dimacs", help="save the DIMACS formula to a file")

    args = parser.parse_args(argv)

    try:
        preferences = load_preferences(args.instance)
        pairs, clauses = encode(preferences)
        formula = dimacs(pairs, clauses)

        if args.dimacs:
            with open(args.dimacs, "w", encoding="ascii", newline="\n") as output:
                output.write(formula)

            print(f"Wrote {len(pairs)} variables and {len(clauses)} clauses to {args.dimacs}")

        else:
            print(formula, end="")

    except (InstanceError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
