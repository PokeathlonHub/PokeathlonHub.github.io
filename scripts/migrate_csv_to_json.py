#!/usr/bin/env python3
"""
Migration script: Convert CSV-based records to player-centric JSON format.

This script reads all 6 CSV files containing Pokeathlon records and creates
a unified players.json file with all player data in one place.
"""

import csv
import json
import os
from datetime import datetime
from collections import defaultdict

# Event-to-course mapping
EVENT_TO_SLUG = {
    'Hurdle Dash': 'hurdle-dash',
    'Pennant Capture': 'pennant-capture',
    'Circle Push': 'circle-push',
    'Block Smash': 'block-smash',
    'Disc Catch': 'disc-catch',
    'Lamp Jump': 'lamp-jump',
    'Relay Run': 'relay-run',
    'Ring Drop': 'ring-drop',
    'Snow Throw': 'snow-throw',
    'Goal Roll': 'goal-roll'
}

COURSE_EVENTS = {
    'speed': ['hurdle-dash', 'pennant-capture', 'relay-run'],
    'power': ['block-smash', 'circle-push', 'goal-roll'],
    'skill': ['snow-throw', 'goal-roll', 'pennant-capture'],
    'stamina': ['ring-drop', 'relay-run', 'block-smash'],
    'jump': ['lamp-jump', 'disc-catch', 'hurdle-dash']
}


def parse_number(value):
    """Parse a number from string, handling commas as decimal separators."""
    if not value or value.strip() == '':
        return None
    try:
        return float(value.replace(",", "."))
    except (ValueError, AttributeError):
        return None


def parse_date(value):
    """Parse a date from DD/MM/YYYY format."""
    if not value or value.strip() == '':
        return None
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except (ValueError, AttributeError):
        return None


def format_date(date_obj):
    """Format date object to ISO format string."""
    if date_obj:
        return date_obj.isoformat()
    return None


def get_proof_info(photo_val, link):
    """Determine proof type and return proof object."""
    if not link or link.strip() == '':
        return None

    link = link.strip()
    if photo_val and photo_val.lower() == 'y':
        if 'youtube.com' in link or 'youtu.be' in link:
            proof_type = 'video'
        else:
            proof_type = 'photo'
    else:
        proof_type = 'claimed'

    return {'type': proof_type, 'url': link}


def normalize_player_name(name):
    """Normalize player name for consistent matching."""
    if not name:
        return None
    name = name.strip()
    # Remove common prefixes/tags in brackets
    # But keep the original name for display
    return name


def read_course_csv(filepath, course_id, event_names):
    """Read a course CSV file and return records grouped by player."""
    records = []

    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found")
        return records

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)

        for row in rows[1:]:  # Skip header
            if len(row) < 7:
                continue

            player = normalize_player_name(row[0])
            if not player:
                continue

            total_score = parse_number(row[1])
            if total_score is None:
                continue

            event1 = parse_number(row[2]) if len(row) > 2 else None
            event2 = parse_number(row[3]) if len(row) > 3 else None
            event3 = parse_number(row[4]) if len(row) > 4 else None
            bonus = parse_number(row[5]) if len(row) > 5 else None
            date = parse_date(row[6]) if len(row) > 6 else None
            link = row[7] if len(row) > 7 else ''
            country = row[8] if len(row) > 8 else 'Unknown'
            photo = row[9] if len(row) > 9 else 'n'

            event_scores = {}
            if event1 is not None:
                event_scores[event_names[0]] = int(event1)
            if event2 is not None:
                event_scores[event_names[1]] = int(event2)
            if event3 is not None:
                event_scores[event_names[2]] = int(event3)

            records.append({
                'player': player,
                'course': course_id,
                'totalScore': int(total_score),
                'eventScores': event_scores,
                'bonusPoints': int(bonus) if bonus else None,
                'date': date,
                'country': country.strip() if country else 'Unknown',
                'proof': get_proof_info(photo, link)
            })

    return records


def read_events_csv(filepath):
    """Read the events CSV file and return records grouped by player."""
    records = []

    event_columns = {
        'hurdle-dash': 1,
        'pennant-capture': 2,
        'circle-push': 3,
        'block-smash': 4,
        'disc-catch': 5,
        'lamp-jump': 6,
        'relay-run': 7,
        'ring-drop': 8,
        'snow-throw': 9,
        'goal-roll': 10
    }

    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found")
        return records

    with open(filepath, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)

        for row in rows[1:]:  # Skip header
            if len(row) < 12:
                continue

            player = normalize_player_name(row[0])
            if not player:
                continue

            date = parse_date(row[11]) if len(row) > 11 else None
            link = row[12] if len(row) > 12 else ''
            country = row[13] if len(row) > 13 else 'Unknown'

            # For events CSV, we don't have a photo column in the same position
            # Check if any score values exist
            for event_id, col_idx in event_columns.items():
                if col_idx < len(row):
                    score = parse_number(row[col_idx])
                    if score is not None:
                        records.append({
                            'player': player,
                            'event': event_id,
                            'score': score,
                            'date': date,
                            'country': country.strip() if country else 'Unknown',
                            'proof': get_proof_info('n', link)  # Events CSV doesn't have photo column per-event
                        })

    return records


def build_player_profiles(course_records, event_records):
    """Build unified player profiles from all records."""
    players = defaultdict(lambda: {
        'name': None,
        'country': 'Unknown',
        'firstRecordDate': None,
        'lastActiveDate': None,
        'status': 'active',
        'courseRecords': {
            'speed': [],
            'power': [],
            'skill': [],
            'stamina': [],
            'jump': []
        },
        'eventRecords': {
            'hurdle-dash': [],
            'pennant-capture': [],
            'circle-push': [],
            'block-smash': [],
            'disc-catch': [],
            'lamp-jump': [],
            'relay-run': [],
            'ring-drop': [],
            'snow-throw': [],
            'goal-roll': []
        },
        'statistics': {
            'totalRecordsSubmitted': 0,
            'currentWorldRecords': 0,
            'personalBests': {}
        },
        'progression': []
    })

    # Process course records
    for record in course_records:
        player_name = record['player']
        player = players[player_name]
        player['name'] = player_name

        if record['country'] and record['country'] != 'Unknown':
            player['country'] = record['country']

        course_record = {
            'totalScore': record['totalScore'],
            'eventScores': record['eventScores'],
            'bonusPoints': record['bonusPoints'],
            'date': format_date(record['date']),
            'proof': record['proof']
        }

        player['courseRecords'][record['course']].append(course_record)
        player['statistics']['totalRecordsSubmitted'] += 1

        # Update date tracking
        if record['date']:
            if player['firstRecordDate'] is None or record['date'] < datetime.fromisoformat(player['firstRecordDate']).date() if player['firstRecordDate'] else True:
                player['firstRecordDate'] = format_date(record['date'])
            if player['lastActiveDate'] is None or record['date'] > datetime.fromisoformat(player['lastActiveDate']).date() if player['lastActiveDate'] else True:
                player['lastActiveDate'] = format_date(record['date'])

        # Update personal bests for courses
        course_key = record['course']
        current_pb = player['statistics']['personalBests'].get(course_key)
        if current_pb is None or record['totalScore'] > current_pb:
            player['statistics']['personalBests'][course_key] = record['totalScore']

    # Process event records
    for record in event_records:
        player_name = record['player']
        player = players[player_name]
        player['name'] = player_name

        if record['country'] and record['country'] != 'Unknown':
            if player['country'] == 'Unknown':
                player['country'] = record['country']

        event_record = {
            'score': record['score'],
            'date': format_date(record['date']),
            'proof': record['proof']
        }

        player['eventRecords'][record['event']].append(event_record)
        player['statistics']['totalRecordsSubmitted'] += 1

        # Update date tracking
        if record['date']:
            first_date = player['firstRecordDate']
            if first_date is None:
                player['firstRecordDate'] = format_date(record['date'])
            elif record['date'] < datetime.fromisoformat(first_date).date():
                player['firstRecordDate'] = format_date(record['date'])

            last_date = player['lastActiveDate']
            if last_date is None:
                player['lastActiveDate'] = format_date(record['date'])
            elif record['date'] > datetime.fromisoformat(last_date).date():
                player['lastActiveDate'] = format_date(record['date'])

        # Update personal bests for events
        event_key = record['event']
        current_pb = player['statistics']['personalBests'].get(event_key)
        is_lower_better = event_key == 'hurdle-dash'

        if current_pb is None:
            player['statistics']['personalBests'][event_key] = record['score']
        elif is_lower_better and record['score'] < current_pb:
            player['statistics']['personalBests'][event_key] = record['score']
        elif not is_lower_better and record['score'] > current_pb:
            player['statistics']['personalBests'][event_key] = record['score']

    return dict(players)


def calculate_current_world_records(players):
    """Calculate which players currently hold world records."""
    # Find best scores for each course and event
    course_bests = {}
    event_bests = {}

    for player_name, player in players.items():
        # Check course records
        for course_id in ['speed', 'power', 'skill', 'stamina', 'jump']:
            records = player['courseRecords'][course_id]
            if records:
                best = max(r['totalScore'] for r in records)
                if course_id not in course_bests or best > course_bests[course_id]['score']:
                    course_bests[course_id] = {'player': player_name, 'score': best}

        # Check event records
        for event_id in player['eventRecords'].keys():
            records = player['eventRecords'][event_id]
            if records:
                is_lower_better = event_id == 'hurdle-dash'
                if is_lower_better:
                    best = min(r['score'] for r in records)
                    if event_id not in event_bests or best < event_bests[event_id]['score']:
                        event_bests[event_id] = {'player': player_name, 'score': best}
                else:
                    best = max(r['score'] for r in records)
                    if event_id not in event_bests or best > event_bests[event_id]['score']:
                        event_bests[event_id] = {'player': player_name, 'score': best}

    # Update player statistics
    for player_name, player in players.items():
        count = 0
        for course_id, best_info in course_bests.items():
            if best_info['player'] == player_name:
                count += 1
        for event_id, best_info in event_bests.items():
            if best_info['player'] == player_name:
                count += 1
        player['statistics']['currentWorldRecords'] = count

    return players


def build_progression(players):
    """Build progression timeline for each player."""
    for player_name, player in players.items():
        progression = []

        # Gather all records with dates
        for course_id in ['speed', 'power', 'skill', 'stamina', 'jump']:
            records = sorted(
                [r for r in player['courseRecords'][course_id] if r['date']],
                key=lambda r: r['date']
            )

            prev_score = None
            for record in records:
                if prev_score is None or record['totalScore'] > prev_score:
                    progression.append({
                        'date': record['date'],
                        'category': course_id,
                        'type': 'course',
                        'event': 'new_pb' if prev_score else 'first_record',
                        'previousScore': prev_score,
                        'newScore': record['totalScore']
                    })
                    prev_score = record['totalScore']

        for event_id in player['eventRecords'].keys():
            records = sorted(
                [r for r in player['eventRecords'][event_id] if r['date']],
                key=lambda r: r['date']
            )

            is_lower_better = event_id == 'hurdle-dash'
            prev_score = None
            for record in records:
                is_improvement = False
                if prev_score is None:
                    is_improvement = True
                elif is_lower_better and record['score'] < prev_score:
                    is_improvement = True
                elif not is_lower_better and record['score'] > prev_score:
                    is_improvement = True

                if is_improvement:
                    progression.append({
                        'date': record['date'],
                        'category': event_id,
                        'type': 'event',
                        'event': 'new_pb' if prev_score else 'first_record',
                        'previousScore': prev_score,
                        'newScore': record['score']
                    })
                    prev_score = record['score']

        # Sort progression by date
        progression.sort(key=lambda p: p['date'] if p['date'] else '')
        player['progression'] = progression

    return players


def migrate():
    """Main migration function."""
    # Base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_dir = os.path.join(base_dir, 'csv')
    data_dir = os.path.join(base_dir, 'data')

    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)

    print("Starting migration from CSV to player-centric JSON...")

    # Read course CSVs
    course_records = []

    course_configs = [
        ('Pokeathlon WRs - Speed_Course.csv', 'speed', ['hurdle-dash', 'pennant-capture', 'relay-run']),
        ('Pokeathlon WRs - Power_Course.csv', 'power', ['block-smash', 'circle-push', 'goal-roll']),
        ('Pokeathlon WRs - Skill_Course.csv', 'skill', ['snow-throw', 'goal-roll', 'pennant-capture']),
        ('Pokeathlon WRs - Stamina_Course.csv', 'stamina', ['ring-drop', 'relay-run', 'block-smash']),
        ('Pokeathlon WRs - Jump_Course.csv', 'jump', ['lamp-jump', 'disc-catch', 'hurdle-dash'])
    ]

    for csv_file, course_id, event_names in course_configs:
        filepath = os.path.join(csv_dir, csv_file)
        records = read_course_csv(filepath, course_id, event_names)
        course_records.extend(records)
        print(f"  Read {len(records)} records from {csv_file}")

    # Read events CSV
    events_csv = os.path.join(csv_dir, 'Pokeathlon WRs - Events_best_scores.csv')
    event_records = read_events_csv(events_csv)
    print(f"  Read {len(event_records)} event records from Events_best_scores.csv")

    # Build player profiles
    print("Building player profiles...")
    players = build_player_profiles(course_records, event_records)
    print(f"  Created profiles for {len(players)} unique players")

    # Calculate current world records
    print("Calculating current world records...")
    players = calculate_current_world_records(players)

    # Build progression timelines
    print("Building progression timelines...")
    players = build_progression(players)

    # Count total records
    total_course_records = sum(
        sum(len(p['courseRecords'][c]) for c in p['courseRecords'])
        for p in players.values()
    )
    total_event_records = sum(
        sum(len(p['eventRecords'][e]) for e in p['eventRecords'])
        for p in players.values()
    )

    print(f"  Total course records: {total_course_records}")
    print(f"  Total event records: {total_event_records}")

    # Write to JSON
    output_file = os.path.join(data_dir, 'players.json')
    output_data = {
        'metadata': {
            'version': '1.0.0',
            'generatedAt': datetime.now().isoformat(),
            'source': 'csv_migration',
            'totalPlayers': len(players),
            'totalCourseRecords': total_course_records,
            'totalEventRecords': total_event_records
        },
        'players': players
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\nMigration complete! Output written to: {output_file}")
    print(f"Total players: {len(players)}")

    return output_data


if __name__ == '__main__':
    migrate()
