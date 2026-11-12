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


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a Stable Roommates instance")
    parser.add_argument("instance", help="JSON preference file")
    args = parser.parse_args(argv)

    try:
        preferences = load_preferences(args.instance)

    except InstanceError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(f"Valid instance with {len(preferences)} agents:")

    for name, ranked in preferences.items():
        partners = ", ".join(ranked) if ranked else "(none)"
        print(f"  {name}: {partners}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
