#!/usr/bin/env python3
"""
Validate players.json against the JSON schema.

This script validates the data structure before generating HTML pages.
"""

import json
import os
import sys

# Try to import jsonschema for full validation
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


def validate_basic(data):
    """Basic validation without jsonschema library."""
    errors = []

    # Check required top-level keys
    if 'metadata' not in data:
        errors.append("Missing required key: metadata")
    if 'players' not in data:
        errors.append("Missing required key: players")

    if 'metadata' in data:
        metadata = data['metadata']
        for key in ['version', 'generatedAt', 'source']:
            if key not in metadata:
                errors.append(f"Missing required metadata key: {key}")

    if 'players' in data:
        players = data['players']
        if not isinstance(players, dict):
            errors.append("players must be an object")
        else:
            for player_name, player in players.items():
                # Check required player keys
                if 'name' not in player:
                    errors.append(f"Player '{player_name}' missing required key: name")
                if 'courseRecords' not in player:
                    errors.append(f"Player '{player_name}' missing required key: courseRecords")
                if 'eventRecords' not in player:
                    errors.append(f"Player '{player_name}' missing required key: eventRecords")

                # Validate course records structure
                if 'courseRecords' in player:
                    valid_courses = {'speed', 'power', 'skill', 'stamina', 'jump'}
                    for course_id in player['courseRecords'].keys():
                        if course_id not in valid_courses:
                            errors.append(f"Player '{player_name}' has invalid course: {course_id}")

                        records = player['courseRecords'].get(course_id, [])
                        if not isinstance(records, list):
                            errors.append(f"Player '{player_name}' courseRecords.{course_id} must be an array")
                        else:
                            for i, record in enumerate(records):
                                if 'totalScore' not in record:
                                    errors.append(f"Player '{player_name}' courseRecords.{course_id}[{i}] missing totalScore")
                                elif not isinstance(record['totalScore'], (int, float)):
                                    errors.append(f"Player '{player_name}' courseRecords.{course_id}[{i}] totalScore must be a number")
                                elif record['totalScore'] < 0 or record['totalScore'] > 800:
                                    errors.append(f"Player '{player_name}' courseRecords.{course_id}[{i}] totalScore out of range: {record['totalScore']}")

                # Validate event records structure
                if 'eventRecords' in player:
                    valid_events = {
                        'hurdle-dash', 'pennant-capture', 'circle-push', 'block-smash',
                        'disc-catch', 'lamp-jump', 'relay-run', 'ring-drop', 'snow-throw', 'goal-roll'
                    }
                    for event_id in player['eventRecords'].keys():
                        if event_id not in valid_events:
                            errors.append(f"Player '{player_name}' has invalid event: {event_id}")

                        records = player['eventRecords'].get(event_id, [])
                        if not isinstance(records, list):
                            errors.append(f"Player '{player_name}' eventRecords.{event_id} must be an array")
                        else:
                            for i, record in enumerate(records):
                                if 'score' not in record:
                                    errors.append(f"Player '{player_name}' eventRecords.{event_id}[{i}] missing score")
                                elif not isinstance(record['score'], (int, float)):
                                    errors.append(f"Player '{player_name}' eventRecords.{event_id}[{i}] score must be a number")

    return errors


def validate_with_schema(data, schema):
    """Full validation using jsonschema library."""
    try:
        jsonschema.validate(instance=data, schema=schema)
        return []
    except jsonschema.exceptions.ValidationError as e:
        return [f"Schema validation error: {e.message} at {list(e.absolute_path)}"]
    except jsonschema.exceptions.SchemaError as e:
        return [f"Schema error: {e.message}"]


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_file = os.path.join(base_dir, 'data', 'players.json')
    schema_file = os.path.join(base_dir, 'data', 'players.schema.json')

    # Check files exist
    if not os.path.exists(data_file):
        print(f"ERROR: Data file not found: {data_file}")
        sys.exit(1)

    # Load data
    print(f"Loading {data_file}...")
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in {data_file}: {e}")
        sys.exit(1)

    print(f"Loaded {len(data.get('players', {}))} players")

    errors = []

    # Try schema validation if available
    if HAS_JSONSCHEMA and os.path.exists(schema_file):
        print("Using JSON Schema validation...")
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                schema = json.load(f)
            errors = validate_with_schema(data, schema)
        except Exception as e:
            print(f"Warning: Schema validation failed, falling back to basic: {e}")
            errors = validate_basic(data)
    else:
        print("Using basic validation (install jsonschema for full validation)...")
        errors = validate_basic(data)

    # Report results
    if errors:
        print(f"\nValidation FAILED with {len(errors)} error(s):")
        for error in errors[:20]:  # Limit output
            print(f"  - {error}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more errors")
        sys.exit(1)
    else:
        print("\nValidation PASSED!")
        print(f"  - {len(data.get('players', {}))} players")
        print(f"  - {data.get('metadata', {}).get('totalCourseRecords', '?')} course records")
        print(f"  - {data.get('metadata', {}).get('totalEventRecords', '?')} event records")
        sys.exit(0)


if __name__ == '__main__':
    main()
