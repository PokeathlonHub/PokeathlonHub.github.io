#!/usr/bin/env python3
"""
HTML Generator for Pokeathlon World Records

Generates static HTML pages from player-centric JSON data and YAML configuration.
"""

import json
import os
import math
from datetime import datetime, date

# Try to import PyYAML, fall back to basic parsing if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


def load_yaml(filepath):
    """Load a YAML file."""
    if HAS_YAML:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    else:
        # Simple fallback parser for our specific YAML structure
        return parse_yaml_simple(filepath)


def parse_yaml_simple(filepath):
    """Simple YAML parser for our specific config structure."""
    result = {}
    current_section = None
    current_item = None
    current_subitem = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.rstrip()
            if not stripped or stripped.startswith('#'):
                continue

            indent = len(line) - len(line.lstrip())

            if indent == 0 and ':' in stripped:
                key = stripped.split(':')[0].strip()
                result[key] = {}
                current_section = key
                current_item = None
            elif indent == 2 and ':' in stripped:
                key = stripped.split(':')[0].strip()
                value = stripped.split(':', 1)[1].strip() if ':' in stripped else None
                if current_section:
                    if value and value != '':
                        result[current_section][key] = parse_yaml_value(value)
                    else:
                        result[current_section][key] = {}
                    current_item = key
                    current_subitem = None
            elif indent == 4 and ':' in stripped:
                key = stripped.split(':')[0].strip()
                value = stripped.split(':', 1)[1].strip() if ':' in stripped else ''
                if current_section and current_item:
                    if isinstance(result[current_section][current_item], dict):
                        if value and not value.startswith('-'):
                            result[current_section][current_item][key] = parse_yaml_value(value)
                        else:
                            result[current_section][current_item][key] = []
                        current_subitem = key
            elif indent == 4 and stripped.startswith('- '):
                value = stripped[2:].strip()
                if current_section and current_item and current_subitem:
                    result[current_section][current_item][current_subitem].append(value)
            elif indent == 6 and ':' in stripped:
                key = stripped.split(':')[0].strip()
                value = stripped.split(':', 1)[1].strip()
                if current_section and current_item and current_subitem:
                    if not isinstance(result[current_section][current_item][current_subitem], dict):
                        result[current_section][current_item][current_subitem] = {}
                    result[current_section][current_item][current_subitem][key] = parse_yaml_value(value)

    return result


def parse_yaml_value(value):
    """Parse a YAML value to appropriate Python type."""
    if value in ('true', 'True'):
        return True
    if value in ('false', 'False'):
        return False
    if value in ('null', 'None', '~'):
        return None
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


def load_players(filepath):
    """Load players.json data."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_config():
    """Load configuration from YAML files."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_dir, 'data', 'config')

    courses_file = os.path.join(config_dir, 'courses.yaml')
    events_file = os.path.join(config_dir, 'events.yaml')

    courses = load_yaml(courses_file).get('courses', {})
    events = load_yaml(events_file).get('events', {})

    return {'courses': courses, 'events': events}


def parse_date(date_str):
    """Parse an ISO date string to date object."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str).date()
    except (ValueError, TypeError):
        return None


def format_date(date_obj, fmt="%d/%m/%Y"):
    """Format a date object to string."""
    if date_obj:
        return date_obj.strftime(fmt)
    return '--'


def get_proof_type(proof):
    """Get proof type from proof object."""
    if not proof:
        return 'claimed'
    return proof.get('type', 'claimed')


def format_proof_link(proof, is_event=False):
    """Format proof link for HTML output."""
    if not proof or not proof.get('url'):
        return 'N/A'

    url = proof['url']
    proof_type = proof.get('type', 'claimed')

    if proof_type == 'video':
        return f'<a href="{url}">Video</a>'
    elif proof_type == 'photo':
        return f'<a href="{url}">Photo</a>'
    else:
        return f'<a href="{url}">{"Link" if is_event else "Claimed Only"}</a>'


def calculate_points(score, event_id, events_config):
    """Calculate points from raw score using event formula."""
    event_config = events_config.get(event_id, {})
    max_points = event_config.get('max_points', 200)

    formulas = {
        'hurdle-dash': lambda s: math.floor(11500 / s) if s > 0 else 0,
        'pennant-capture': lambda s: int(s * 3),
        'circle-push': lambda s: int(s * 3),
        'block-smash': lambda s: int(s),
        'disc-catch': lambda s: int(150 - (1500 / (s + 12.5))),
        'lamp-jump': lambda s: math.floor(s / 3.5),
        'relay-run': lambda s: int(s * 10),
        'ring-drop': lambda s: int(s * 1.5),
        'snow-throw': lambda s: int(s * 3),
        'goal-roll': lambda s: int(100 + (s * 5))
    }

    formula_fn = formulas.get(event_id, lambda s: int(s))
    return min(max_points, formula_fn(score))


def get_medal_for_record(record, records_list, lower_is_better=False):
    """
    Determine if a record should have a medal icon and which one.
    Returns: '🥇', '🥈', '🥉', or None

    Medals are assigned using the strict top 3 logic:
    1. Include top 3 positions by score
    2. If multiple records tie for 3rd place on SAME date, include all
    3. If records tie for 3rd place on DIFFERENT dates, only earliest
    """
    if not records_list:
        return None

    # Determine which score field to use
    score_field = 'total_score' if 'total_score' in record else 'score'

    # Build strict top 3 from the record history
    candidates = [(r.get('player', ''), r.get(score_field), r) for r in records_list]
    strict_top3 = build_strict_top3(candidates, lower_is_better)

    # Find position in strict top 3 by comparing record identity
    for i, entry in enumerate(strict_top3):
        if entry[2] is record:
            medals = ['🥇', '🥈', '🥉']
            return medals[i] if i < 3 else None

    # Record is not in strict top 3
    return None


def build_strict_top3(candidates, lower_is_better=False):
    """
    Build strict top 3 list with same-date tie exception.

    Rules:
    1. Include top 3 positions by score
    2. If multiple records tie for 3rd place on SAME date, include all
    3. If records tie for 3rd place on DIFFERENT dates, only earliest

    Returns: List of (player, score, record) tuples for strict top 3
    """
    if len(candidates) < 3:
        return candidates

    # Sort by score (desc/asc), then by date ascending
    if lower_is_better:
        candidates.sort(key=lambda x: (x[1], x[2]['date']))
    else:
        candidates.sort(key=lambda x: (-x[1], x[2]['date']))

    # Get 3rd position details
    third_score = candidates[2][1]
    third_date = candidates[2][2]['date']

    # Include top 2 + all same-score same-date 3rd place ties
    strict_top3 = candidates[:2]

    for entry in candidates[2:]:
        matches_score = entry[1] == third_score
        matches_date = entry[2]['date'] == third_date

        if matches_score and matches_date:
            strict_top3.append(entry)
        elif (entry[1] < third_score and not lower_is_better) or \
             (entry[1] > third_score and lower_is_better):
            break  # No more possible ties

    return strict_top3


def get_course_leaderboard(players_data, course_id, config):
    """
    Get course leaderboard with best score per player and historical statistics.
    Returns: (all_records, best_per_player, first_holder_days, top23_presence_days)
    """
    players = players_data.get('players', {})
    all_records = []

    # Collect all records with dates
    for player_name, player in players.items():
        course_records = player.get('courseRecords', {}).get(course_id, [])
        for record in course_records:
            record_date = parse_date(record.get('date'))
            if record_date and record.get('totalScore'):
                all_records.append({
                    'player': player_name,
                    'total_score': record['totalScore'],
                    'event_scores': record.get('eventScores', {}),
                    'bonus_points': record.get('bonusPoints'),
                    'date': record_date,
                    'proof': record.get('proof')
                })

    # Sort by date
    all_records.sort(key=lambda r: r['date'])

    # Calculate leaderboard statistics
    top3_extended = []  # For record history
    top3_strict = []    # For time tracking
    first_place_periods = []
    top23_periods = {}
    current_first_holder = None
    current_first_start = None
    current_top23_holders = {}
    record_improvements = []

    for record in all_records:
        # === EXTENDED TOP 3 (Record History) ===
        previous_extended = top3_extended.copy()
        top3_extended.append((record['player'], record['total_score'], record))
        top3_extended.sort(key=lambda x: -x[1])

        if len(top3_extended) >= 3:
            third_best_score = top3_extended[2][1]
            top3_extended = [e for e in top3_extended if e[1] >= third_best_score]

        # Deduplicate: keep only one entry per player per score
        seen_player_scores = {}
        deduplicated_extended = []
        for player, score, rec in top3_extended:
            key = (player, score)
            if key not in seen_player_scores:
                seen_player_scores[key] = True
                deduplicated_extended.append((player, score, rec))
        top3_extended = deduplicated_extended

        # Record if extended leaderboard changed (for record history)
        if [(p, s) for p, s, _ in top3_extended] != [(p, s) for p, s, _ in previous_extended]:
            record_improvements.append(record)

        # === STRICT TOP 3 (Time Tracking) ===
        previous_strict = top3_strict.copy()

        candidates = top3_strict.copy()
        candidates.append((record['player'], record['total_score'], record))
        top3_strict = build_strict_top3(candidates, lower_is_better=False)

        # Deduplicate: keep only one entry per player per score
        seen_player_scores = {}
        deduplicated_strict = []
        for player, score, rec in top3_strict:
            key = (player, score)
            if key not in seen_player_scores:
                seen_player_scores[key] = True
                deduplicated_strict.append((player, score, rec))
        top3_strict = deduplicated_strict

        # Track time periods if strict leaderboard changed
        if [(p, s) for p, s, _ in top3_strict] != [(p, s) for p, s, _ in previous_strict]:
            new_top23_names = set(entry[0] for entry in top3_strict[1:])

            # End periods for players no longer in positions 2-3
            for player, start_date in list(current_top23_holders.items()):
                if player not in new_top23_names:
                    if player not in top23_periods:
                        top23_periods[player] = []
                    top23_periods[player].append((start_date, record['date']))

            # Handle first place changes
            new_first = top3_strict[0]
            if previous_strict and previous_strict[0][0] != new_first[0]:
                if current_first_holder and current_first_start:
                    first_place_periods.append((current_first_holder, current_first_start, record['date']))
                current_first_holder = new_first[0]
                current_first_start = record['date']
            elif not previous_strict:
                current_first_holder = new_first[0]
                current_first_start = record['date']

            # Start new periods for players entering positions 2-3
            new_top23_holders = {}
            for entry in top3_strict[1:]:
                player = entry[0]
                new_top23_holders[player] = current_top23_holders.get(player, record['date'])
            current_top23_holders = new_top23_holders

    # End final periods
    if all_records:
        final_date = date.today()
        for player, start_date in current_top23_holders.items():
            if player not in top23_periods:
                top23_periods[player] = []
            top23_periods[player].append((start_date, final_date))

        if current_first_holder and current_first_start:
            first_place_periods.append((current_first_holder, current_first_start, final_date))

    # Calculate total days
    first_holder_days = {}
    top23_presence_days = {}

    for player, start_date, end_date in first_place_periods:
        days = max(0, (end_date - start_date).days)
        first_holder_days[player] = first_holder_days.get(player, 0) + days

    for player, periods in top23_periods.items():
        total_days = sum(max(0, (end_date - start_date).days) for start_date, end_date in periods)
        top23_presence_days[player] = total_days

    # Get current best per player
    best_per_player = {}
    for player_name, player in players.items():
        course_records = player.get('courseRecords', {}).get(course_id, [])
        if course_records:
            best = max(course_records, key=lambda r: r.get('totalScore', 0))
            best_per_player[player_name] = best

    return all_records, record_improvements, first_holder_days, top23_presence_days


def get_event_leaderboard(players_data, event_id, events_config):
    """
    Get event leaderboard with best score per player and historical statistics.
    """
    players = players_data.get('players', {})
    event_config = events_config.get(event_id, {})
    lower_is_better = event_config.get('lower_is_better', False)
    all_records = []

    # Collect all records with dates
    for player_name, player in players.items():
        event_records = player.get('eventRecords', {}).get(event_id, [])
        for record in event_records:
            record_date = parse_date(record.get('date'))
            if record_date and record.get('score') is not None:
                all_records.append({
                    'player': player_name,
                    'score': record['score'],
                    'date': record_date,
                    'proof': record.get('proof')
                })

    # Sort by date
    all_records.sort(key=lambda r: r['date'])

    # Calculate leaderboard statistics (similar to course but for events)
    top3_extended = []  # For record history
    top3_strict = []    # For time tracking
    first_place_periods = []
    top23_periods = {}
    current_first_holder = None
    current_first_start = None
    current_top23_holders = {}
    record_improvements = []

    for record in all_records:
        # === EXTENDED TOP 3 (Record History) ===
        previous_extended = top3_extended.copy()
        top3_extended.append((record['player'], record['score'], record))
        if lower_is_better:
            top3_extended.sort(key=lambda x: (x[1], all_records.index(x[2]) if x[2] in all_records else 0))
        else:
            top3_extended.sort(key=lambda x: (-x[1], all_records.index(x[2]) if x[2] in all_records else 0))

        if len(top3_extended) >= 3:
            third_best_score = top3_extended[2][1]
            if lower_is_better:
                top3_extended = [e for e in top3_extended if e[1] <= third_best_score]
            else:
                top3_extended = [e for e in top3_extended if e[1] >= third_best_score]

        # Deduplicate: keep only one entry per player per score
        seen_player_scores = {}
        deduplicated_extended = []
        for player, score, rec in top3_extended:
            key = (player, score)
            if key not in seen_player_scores:
                seen_player_scores[key] = True
                deduplicated_extended.append((player, score, rec))
        top3_extended = deduplicated_extended

        # Record if extended leaderboard changed (for record history)
        if [(p, s) for p, s, _ in top3_extended] != [(p, s) for p, s, _ in previous_extended]:
            record_improvements.append(record)

        # === STRICT TOP 3 (Time Tracking) ===
        previous_strict = top3_strict.copy()

        candidates = top3_strict.copy()
        candidates.append((record['player'], record['score'], record))
        top3_strict = build_strict_top3(candidates, lower_is_better=lower_is_better)

        # Deduplicate: keep only one entry per player per score
        seen_player_scores = {}
        deduplicated_strict = []
        for player, score, rec in top3_strict:
            key = (player, score)
            if key not in seen_player_scores:
                seen_player_scores[key] = True
                deduplicated_strict.append((player, score, rec))
        top3_strict = deduplicated_strict

        # Track time periods if strict leaderboard changed
        if [(p, s) for p, s, _ in top3_strict] != [(p, s) for p, s, _ in previous_strict]:
            new_top23_names = set(entry[0] for entry in top3_strict[1:])

            for player, start_date in list(current_top23_holders.items()):
                if player not in new_top23_names:
                    if player not in top23_periods:
                        top23_periods[player] = []
                    top23_periods[player].append((start_date, record['date']))

            new_first = top3_strict[0]
            if previous_strict and previous_strict[0][0] != new_first[0]:
                if current_first_holder and current_first_start:
                    first_place_periods.append((current_first_holder, current_first_start, record['date']))
                current_first_holder = new_first[0]
                current_first_start = record['date']
            elif not previous_strict:
                current_first_holder = new_first[0]
                current_first_start = record['date']

            new_top23_holders = {}
            for entry in top3_strict[1:]:
                player = entry[0]
                new_top23_holders[player] = current_top23_holders.get(player, record['date'])
            current_top23_holders = new_top23_holders

    # End final periods
    if all_records:
        final_date = date.today()
        for player, start_date in current_top23_holders.items():
            if player not in top23_periods:
                top23_periods[player] = []
            top23_periods[player].append((start_date, final_date))

        if current_first_holder and current_first_start:
            first_place_periods.append((current_first_holder, current_first_start, final_date))

    # Calculate total days
    first_holder_days = {}
    top23_presence_days = {}

    for player, start_date, end_date in first_place_periods:
        days = max(0, (end_date - start_date).days)
        first_holder_days[player] = first_holder_days.get(player, 0) + days

    for player, periods in top23_periods.items():
        total_days = sum(max(0, (end_date - start_date).days) for start_date, end_date in periods)
        top23_presence_days[player] = total_days

    return all_records, record_improvements, first_holder_days, top23_presence_days


def get_current_course_record(players_data, course_id):
    """Get the current world record for a course."""
    players = players_data.get('players', {})
    best_record = None
    best_score = -1

    for player_name, player in players.items():
        course_records = player.get('courseRecords', {}).get(course_id, [])
        for record in course_records:
            score = record.get('totalScore', 0)
            record_date = parse_date(record.get('date'))

            if score > best_score:
                best_score = score
                best_record = {
                    'player': player_name,
                    'total_score': score,
                    'event_scores': record.get('eventScores', {}),
                    'bonus_points': record.get('bonusPoints'),
                    'date': record_date,
                    'proof': record.get('proof')
                }
            elif score == best_score and record_date < best_record['date']:
                best_record = {
                    'player': player_name,
                    'total_score': score,
                    'event_scores': record.get('eventScores', {}),
                    'bonus_points': record.get('bonusPoints'),
                    'date': record_date,
                    'proof': record.get('proof')
                }

    return best_record


def get_current_event_record(players_data, event_id, events_config):
    """Get the current world record for an event."""
    event_config = events_config.get(event_id, {})

    # Check for fixed record (Circle Push, Ring Drop)
    if event_config.get('fixed_record'):
        fixed = event_config['fixed_record']
        return {
            'player': fixed['player'],
            'score': fixed['score'],
            'points': fixed['points'],
            'date': parse_date(fixed['date']),
            'proof': None
        }

    players = players_data.get('players', {})
    lower_is_better = event_config.get('lower_is_better', False)
    best_record = None
    best_score = None

    for player_name, player in players.items():
        event_records = player.get('eventRecords', {}).get(event_id, [])
        for record in event_records:
            score = record.get('score')
            if score is None:
                continue

            record_date = parse_date(record.get('date'))

            if best_score is None:
                best_score = score
                best_record = {
                    'player': player_name,
                    'score': score,
                    'points': calculate_points(score, event_id, events_config),
                    'date': record_date,
                    'proof': record.get('proof')
                }
            elif lower_is_better and score < best_score:
                best_score = score
                best_record = {
                    'player': player_name,
                    'score': score,
                    'points': calculate_points(score, event_id, events_config),
                    'date': record_date,
                    'proof': record.get('proof')
                }
            elif lower_is_better and score == best_score and record_date < best_record['date']:
                best_record = {
                    'player': player_name,
                    'score': score,
                    'points': calculate_points(score, event_id, events_config),
                    'date': record_date,
                    'proof': record.get('proof')
                }
            elif not lower_is_better and score > best_score:
                best_score = score
                best_record = {
                    'player': player_name,
                    'score': score,
                    'points': calculate_points(score, event_id, events_config),
                    'date': record_date,
                    'proof': record.get('proof')
                }
            elif not lower_is_better and score == best_score and record_date < best_record['date']:
                best_record = {
                    'player': player_name,
                    'score': score,
                    'points': calculate_points(score, event_id, events_config),
                    'date': record_date,
                    'proof': record.get('proof')
                }

    return best_record


def generate_course_html(course_id, course_config, players_data, events_config, output_file):
    """Generate HTML page for a course."""
    display_name = course_config.get('display_name', course_id.title() + ' Course')
    event_ids = course_config.get('events', [])

    # Get event display names
    event_names = []
    for eid in event_ids:
        evt_cfg = events_config.get(eid, {})
        event_names.append(evt_cfg.get('display_name', eid.replace('-', ' ').title()))

    # Get leaderboard data
    all_records, record_history, first_holder_days, top23_presence_days = get_course_leaderboard(
        players_data, course_id, course_config
    )

    # Get current record
    current_record = get_current_course_record(players_data, course_id)

    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>{display_name} - Pokéathlon WRs</title>
    <link rel="stylesheet" href="../style.css">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="../championship-trophy.svg" type="image/svg+xml">
</head>
<body>
    <button id="themeToggle" class="theme-toggle" aria-label="Toggle dark/light theme">🌙</button>
    <nav><a href="../index.html">← Back to All Events</a></nav>

    <h1>{display_name}</h1>

    <div class="filter-container">
        <h3>Filter by Proof Type</h3>
        <div class="filter-options">
            <div class="filter-option">
                <input type="radio" id="all-record" name="proofFilter" value="all-record" checked>
                <label for="all-record">ALL RECORDS</label>
            </div>
            <div class="filter-option">
                <input type="radio" id="verified-record" name="proofFilter" value="verified-record">
                <label for="verified-record">VERIFIED RECORD</label>
            </div>
            <div class="filter-option">
                <input type="radio" id="photo" name="proofFilter" value="photo">
                <label for="photo">PHOTO</label>
            </div>
            <div class="filter-option">
                <input type="radio" id="video" name="proofFilter" value="video">
                <label for="video">VIDEO</label>
            </div>
            <div class="filter-option">
                <input type="radio" id="livestream" name="proofFilter" value="livestream">
                <label for="livestream">LIVESTREAM</label>
            </div>
        </div>
        <div class="filter-info">
            Choose how strict you want the proof requirements to be.
        </div>
    </div>
    <div class="stats" id="stats">
        Showing verified records
    </div>'''

    if current_record:
        proof_type = get_proof_type(current_record['proof'])
        proof_link = format_proof_link(current_record['proof'])

        event_score_1 = current_record['event_scores'].get(event_ids[0], '--')
        event_score_2 = current_record['event_scores'].get(event_ids[1], '--')
        event_score_3 = current_record['event_scores'].get(event_ids[2], '--')
        if event_score_1 != '--':
            event_score_1 = int(event_score_1)
        if event_score_2 != '--':
            event_score_2 = int(event_score_2)
        if event_score_3 != '--':
            event_score_3 = int(event_score_3)

        html_content += f'''

    <h2>Current Record</h2>
    <div class="table-wrapper">
    <table>
        <thead>
            <tr>
                <th>Player</th>
                <th>Total Score</th>
                <th>{event_names[0]}</th>
                <th>{event_names[1]}</th>
                <th>{event_names[2]}</th>
                <th>Bonus Points</th>
                <th>Date</th>
                <th>Proof</th>
            </tr>
        </thead>
        <tbody>
            <tr data-proof="{proof_type}">
                <td>{current_record['player']}</td>
                <td>{int(current_record['total_score'])}</td>
                <td>{event_score_1}</td>
                <td>{event_score_2}</td>
                <td>{event_score_3}</td>
                <td>{int(current_record['bonus_points']) if current_record['bonus_points'] else '--'}</td>
                <td>{format_date(current_record['date'])}</td>
                <td>{proof_link}</td>
            </tr>
        </tbody>
    </table>
    </div>'''

    html_content += f'''

    <h2>Record History</h2>
    <div class="table-wrapper">
    <table>
        <thead>
            <tr>
                <th>Player</th>
                <th data-sort-method='number'>Total Score</th>
                <th data-sort-method='number'>{event_names[0]}</th>
                <th data-sort-method='number'>{event_names[1]}</th>
                <th data-sort-method='number'>{event_names[2]}</th>
                <th data-sort-method='number'>Bonus Points</th>
                <th>Date</th>
                <th>Proof</th>
            </tr>
        </thead>
        <tbody>'''

    for record in record_history:
        proof_type = get_proof_type(record['proof'])
        proof_link = format_proof_link(record['proof'])

        event_score_1 = record['event_scores'].get(event_ids[0], '--')
        event_score_2 = record['event_scores'].get(event_ids[1], '--')
        event_score_3 = record['event_scores'].get(event_ids[2], '--')
        if event_score_1 != '--':
            event_score_1 = int(event_score_1)
        if event_score_2 != '--':
            event_score_2 = int(event_score_2)
        if event_score_3 != '--':
            event_score_3 = int(event_score_3)

        # Add medal icons for top 3 WR holders (courses use higher scores as better)
        medal = get_medal_for_record(record, record_history, lower_is_better=False)
        player_display = f"{medal} {record['player']}" if medal else record['player']

        html_content += f'''
            <tr data-proof="{proof_type}">
                <td>{player_display}</td>
                <td>{int(record['total_score'])}</td>
                <td>{event_score_1}</td>
                <td>{event_score_2}</td>
                <td>{event_score_3}</td>
                <td>{int(record['bonus_points']) if record.get('bonus_points') else '--'}</td>
                <td>{format_date(record['date'])}</td>
                <td>{proof_link}</td>
            </tr>'''

    html_content += '''
        </tbody>
    </table>
    </div>'''

    # Leaderboard statistics
    all_names = set(first_holder_days.keys()) | set(top23_presence_days.keys())
    if all_names:
        html_content += '''

    <h2>Leaderboard Statistics</h2>
    <div class="table-wrapper">
    <table>
        <thead>
            <tr>
                <th>Player</th>
                <th data-sort-method='number'>Number of days at #1</th>
                <th data-sort-method='number'>Number of days in Top 3 (positions 2-3)</th>
            </tr>
        </thead>
        <tbody>'''

        for name in sorted(all_names, key=lambda n: -top23_presence_days.get(n, 0)):
            html_content += f'''
            <tr>
                <td>{name}</td>
                <td>{first_holder_days.get(name, 0)}</td>
                <td>{top23_presence_days.get(name, 0)}</td>
            </tr>'''

        html_content += '''
        </tbody>
    </table>
    </div>'''

    html_content += '''
    <script src="../js/tablesort.min.js"></script>
    <script src="../js/tablesort.number.min.js"></script>
    <script src="../js/tablesort.date.js"></script>
    <script src="../js/sorting-logic.js"></script>
    <script src="../js/theme-toggle.js"></script>
    <script>
        document.querySelectorAll('table').forEach(table => {
            const sort = new Tablesort(table);
        });
    </script>
</body>
</html>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_event_html(event_id, event_config, players_data, events_config, output_file):
    """Generate HTML page for an event."""
    display_name = event_config.get('display_name', event_id.replace('-', ' ').title())
    lower_is_better = event_config.get('lower_is_better', False)

    # Get leaderboard data
    all_records, record_history, first_holder_days, top23_presence_days = get_event_leaderboard(
        players_data, event_id, events_config
    )

    # Get current record
    current_record = get_current_event_record(players_data, event_id, events_config)

    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>{display_name} - Pokeathlon WRs</title>
    <link rel="stylesheet" href="../style.css" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" href="../championship-trophy.svg" type="image/svg+xml">
</head>
<body>
    <button id="themeToggle" class="theme-toggle" aria-label="Toggle dark/light theme">🌙</button>
    <nav><a href="../index.html">← Back to All Events</a></nav>

    <h1>{display_name} WR</h1>

    <h2>Current Record</h2>
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>Score</th>
                    <th>Player</th>
                    <th>Date</th>
                    <th>Proof</th>
                </tr>
            </thead>
            <tbody>'''

    if current_record:
        proof_link = format_proof_link(current_record.get('proof'), is_event=True)
        score_display = current_record['score']
        if event_id in ['hurdle-dash', 'relay-run']:
            score_display = f"{score_display:.1f}".replace('.', ',') if isinstance(score_display, float) else score_display
        html_content += f'''
                <tr>
                    <td>{score_display}</td>
                    <td>{current_record['player']}</td>
                    <td>{format_date(current_record.get('date'), "%Y-%m-%d")}</td>
                    <td>{proof_link}</td>
                </tr>'''

    html_content += '''
            </tbody>
        </table>
    </div>

    <h2>Record History</h2>
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>Player</th>
                    <th>Total Score</th>
                    <th>Date</th>
                    <th>Proof</th>
                </tr>
            </thead>
            <tbody>'''

    for record in record_history:
        proof_link = format_proof_link(record.get('proof'), is_event=True)
        score_display = record['score']
        if event_id in ['hurdle-dash', 'relay-run']:
            score_display = f"{score_display:.1f}".replace('.', ',') if isinstance(score_display, float) else score_display

        # Add medal icons for top 3 WR holders
        medal = get_medal_for_record(record, record_history, lower_is_better)
        player_display = f"{medal} {record['player']}" if medal else record['player']

        html_content += f'''
                <tr>
                    <td>{player_display}</td>
                    <td>{score_display}</td>
                    <td>{format_date(record['date'])}</td>
                    <td>{proof_link}</td>
                </tr>'''

    html_content += '''
            </tbody>
        </table>
    </div>

    <h2>Leaderboard Statistics</h2>
    <div class="table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Number of days at #1</th>
                    <th>Number of days in Top 3</th>
                </tr>
            </thead>
            <tbody>'''

    all_names = set(first_holder_days.keys()) | set(top23_presence_days.keys())
    for name in sorted(all_names, key=lambda n: -top23_presence_days.get(n, 0)):
        html_content += f'''
                <tr>
                    <td>{name}</td>
                    <td>{first_holder_days.get(name, 0)}</td>
                    <td>{top23_presence_days.get(name, 0)}</td>
                </tr>'''

    html_content += '''
            </tbody>
        </table>
    </div>
    <script src="../js/tablesort.min.js"></script>
    <script src="../js/tablesort.number.min.js"></script>
    <script src="../js/tablesort.date.js"></script>
    <script src="../js/theme-toggle.js"></script>
    <script>
        document.querySelectorAll('table').forEach(table => {
            const sort = new Tablesort(table);
        });
    </script>
</body>
</html>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)


def generate_index_html(players_data, config):
    """Generate the main index.html file."""
    courses_config = config.get('courses', {})
    events_config = config.get('events', {})

    # Get course records
    course_records = {}
    for course_id in ['speed', 'power', 'skill', 'stamina', 'jump']:
        record = get_current_course_record(players_data, course_id)
        if record:
            course_config = courses_config.get(course_id, {})
            event_ids = course_config.get('events', [])
            course_records[course_id] = {
                'player': record['player'],
                'total_score': int(record['total_score']),
                'event1_points': int(record['event_scores'].get(event_ids[0], 0)) if record['event_scores'].get(event_ids[0]) else '--',
                'event2_points': int(record['event_scores'].get(event_ids[1], 0)) if record['event_scores'].get(event_ids[1]) else '--',
                'event3_points': int(record['event_scores'].get(event_ids[2], 0)) if record['event_scores'].get(event_ids[2]) else '--',
                'bonus': int(record['bonus_points']) if record['bonus_points'] else '--',
                'date': record['date']
            }

    # Get event records
    event_records = {}
    for event_id in events_config.keys():
        record = get_current_event_record(players_data, event_id, events_config)
        if record:
            event_records[event_id] = record

    # Event formulas for display
    event_formulas = {}
    for event_id, evt_cfg in events_config.items():
        latex = evt_cfg.get('latex', '')
        if latex:
            event_formulas[event_id] = r'\( ' + latex + r' \)'

    # Format last updated timestamp
    last_updated = date.today().strftime("%B %d, %Y")

    html_content = '''<!DOCTYPE html>
<html>
<head>
  <title>Pokeathlon World Records</title>
  <link rel="stylesheet" href="style.css">
  <link rel="icon" href="championship-trophy.svg" type="image/svg+xml">
  <link rel="sitemap" type="application/xml" title="Sitemap" href="https://pokeathlonhub.github.io/sitemap.xml">
  <script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" defer></script>
  <meta name="google-site-verification" content="XzjYyqTL5gndXteUIgnJcXnqW4esQ7C0NCS717ZXt-U" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body>
  <button id="themeToggle" class="theme-toggle" aria-label="Toggle dark/light theme">🌙</button>
  <button id="menuToggle" class="menu-toggle" aria-label="Toggle menu">☰</button>

  <div id="sidebar" class="sidebar">
    <h3 id="coursesToggle">Courses</h3>
    <ul id="coursesMenu">
      <li><a href="courses/speed.html">Speed</a></li>
      <li><a href="courses/power.html">Power</a></li>
      <li><a href="courses/skill.html">Skill</a></li>
      <li><a href="courses/stamina.html">Stamina</a></li>
      <li><a href="courses/jump.html">Jump</a></li>
    </ul>

    <h3 id="eventsToggle">Events</h3>
    <ul id="eventsMenu">
      <li><a href="events/hurdle-dash.html">Hurdle Dash</a></li>
      <li><a href="events/pennant-capture.html">Pennant Capture</a></li>
      <li><a href="events/block-smash.html">Block Smash</a></li>
      <li><a href="events/disc-catch.html">Disc Catch</a></li>
      <li><a href="events/lamp-jump.html">Lamp Jump</a></li>
      <li><a href="events/relay-run.html">Relay Run</a></li>
      <li><a href="events/snow-throw.html">Snow Throw</a></li>
      <li><a href="events/goal-roll.html">Goal Roll</a></li>
    </ul>

    <h3 id="calculatorsToggle">Calculators</h3>
    <ul id="calculatorsMenu">
      <li><a href="calculators/PID.html">PID</a></li>
      <li><a href="calculators/rank-simulator.html">Rank Simulator</a></li>
    </ul>
  </div>

  <h1>Pokeathlon World Records</h1>
  <p>Since the release of HG/SS, Pokeathlon has been an endless source of entertainment for many people. During these years people have shared their PBs in many different forums and websites, our goal is to create the go-to place for pokeathlon enjoyers.</p>
  <p class="last-updated" style="text-align: center; color: #666; font-size: 0.9em; margin-top: 1em;">
    Last updated: ''' + last_updated + '''
  </p>

  <h2>Course World Records</h2>
  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th>Course</th>
          <th>Player</th>
          <th>Total Score</th>
          <th>First event</th>
          <th>Second event</th>
          <th>Third event</th>
          <th>Bonus points</th>
          <th>Date</th>
        </tr>
      </thead>
      <tbody>'''

    for course_name in ['speed', 'power', 'skill', 'stamina', 'jump']:
        display_name = course_name.title()
        if course_name in course_records:
            record = course_records[course_name]
            html_content += f'''
        <tr>
          <td><a href="courses/{course_name}.html">{display_name}</a></td>
          <td>{record['player']}</td>
          <td>{record['total_score']}</td>
          <td>{record['event1_points']}</td>
          <td>{record['event2_points']}</td>
          <td>{record['event3_points']}</td>
          <td>{record['bonus']}</td>
          <td>{format_date(record['date']) if record['date'] else '--'}</td>
        </tr>'''
        else:
            html_content += f'''
        <tr>
          <td><a href="courses/{course_name}.html">{display_name}</a></td>
          <td>–</td>
          <td>–</td>
          <td>–</td>
          <td>–</td>
          <td>–</td>
          <td>–</td>
          <td>–</td>
        </tr>'''

    html_content += '''
      </tbody>
    </table>
  </div>

  <h2>Single Event World Records</h2>
  <div class="table-wrapper">
    <table>
      <thead>
        <tr>
          <th>Event</th>
          <th>Player</th>
          <th>Score</th>
          <th>Points</th>
          <th>Formula</th>
          <th>Date</th>
        </tr>
      </thead>
      <tbody>'''

    event_order = ['hurdle-dash', 'pennant-capture', 'circle-push', 'block-smash',
                   'disc-catch', 'lamp-jump', 'relay-run', 'ring-drop', 'snow-throw', 'goal-roll']

    for event_id in event_order:
        evt_cfg = events_config.get(event_id, {})
        display_name = evt_cfg.get('display_name', event_id.replace('-', ' ').title())
        has_page = evt_cfg.get('has_page', True)

        if event_id in event_records:
            record = event_records[event_id]
            score = record['score']

            if event_id in ['hurdle-dash', 'relay-run']:
                score_display = f"{score:.1f}".replace('.', ',') if isinstance(score, float) else str(score)
            else:
                score_display = str(int(score)) if score == int(score) else str(score)

            if has_page:
                event_cell = f'<td><a href="events/{event_id}.html">{display_name}</a></td>'
            else:
                event_cell = f'<td>{display_name}</td>'

            formula = event_formulas.get(event_id, '–')
            # Add tooltip for goal-roll to explain position points
            if event_id == 'goal-roll':
                formula += ' <span class="tooltip-icon" tabindex="0">?<span class="tooltip-text">Position points: 1st: 100 · 2nd: 80 · 3rd: 70 · 4th: 60</span></span>'

            html_content += f'''
        <tr>
          {event_cell}
          <td>{record['player']}</td>
          <td>{score_display}</td>
          <td>{record['points']}</td>
          <td>{formula}</td>
          <td>{format_date(record.get('date')) if record.get('date') else '--'}</td>
        </tr>'''
        else:
            formula = event_formulas.get(event_id, '–')
            # Add tooltip for goal-roll to explain position points
            if event_id == 'goal-roll':
                formula += ' <span class="tooltip-icon" tabindex="0">?<span class="tooltip-text">Position points: 1st: 100 · 2nd: 80 · 3rd: 70 · 4th: 60</span></span>'
            html_content += f'''
        <tr>
          <td>{display_name}</td>
          <td>–</td>
          <td>–</td>
          <td>–</td>
          <td>{formula}</td>
          <td>–</td>
        </tr>'''

    html_content += '''
      </tbody>
    </table>
  </div>

  <script src="js/tablesort.min.js"></script>
  <script src="js/tablesort.number.min.js"></script>
  <script src="js/tablesort.date.js"></script>
  <script src="js/theme-toggle.js"></script>
  <script src="js/sidebar-menu.js" defer></script>
  <script>
    document.querySelectorAll('table').forEach(table => {
      const sort = new Tablesort(table);
    });
  </script>
</body>
</html>'''

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)


def save_players(filepath, data):
    """Save players.json data."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def update_world_record_counts(players_data, courses_config, events_config):
    """
    Recalculate and update currentWorldRecords for all players.

    A player holds a world record if they have the current best score
    (earliest date wins ties) for any course or event.
    """
    players = players_data.get('players', {})

    # Reset all world record counts to 0
    for player in players.values():
        if 'statistics' not in player:
            player['statistics'] = {}
        player['statistics']['currentWorldRecords'] = 0

    # Count course world records
    for course_id in courses_config.keys():
        record = get_current_course_record(players_data, course_id)
        if record and record['player'] in players:
            players[record['player']]['statistics']['currentWorldRecords'] += 1

    # Count event world records
    for event_id, event_cfg in events_config.items():
        # Skip fixed records (Circle Push, Ring Drop) - those aren't player-held
        if event_cfg.get('fixed_record'):
            continue
        record = get_current_event_record(players_data, event_id, events_config)
        if record and record['player'] in players:
            players[record['player']]['statistics']['currentWorldRecords'] += 1

    # Count how many players have world records
    holders = [(name, p['statistics']['currentWorldRecords'])
               for name, p in players.items()
               if p['statistics'].get('currentWorldRecords', 0) > 0]

    return holders


def generate_all():
    """Generate all HTML files from player-centric data."""
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Load configuration
    print("Loading configuration...")
    config = load_config()
    courses_config = config.get('courses', {})
    events_config = config.get('events', {})

    # Load player data
    print("Loading player data...")
    players_file = os.path.join(base_dir, 'data', 'players.json')
    players_data = load_players(players_file)

    print(f"Loaded {len(players_data.get('players', {}))} players")

    # Update world record counts in player statistics
    print("Updating world record counts...")
    holders = update_world_record_counts(players_data, courses_config, events_config)
    print(f"  Found {len(holders)} players with world records")
    save_players(players_file, players_data)

    # Ensure output directories exist
    os.makedirs('courses', exist_ok=True)
    os.makedirs('events', exist_ok=True)

    # Generate course pages
    print("Generating course pages...")
    for course_id, course_cfg in courses_config.items():
        output_file = course_cfg.get('output', f'courses/{course_id}.html')
        try:
            generate_course_html(course_id, course_cfg, players_data, events_config, output_file)
            print(f"  Generated {output_file}")
        except Exception as e:
            print(f"  Error generating {output_file}: {e}")

    # Generate event pages
    print("Generating event pages...")
    for event_id, event_cfg in events_config.items():
        if not event_cfg.get('has_page', True):
            continue
        output_file = event_cfg.get('output', f'events/{event_id}.html')
        try:
            generate_event_html(event_id, event_cfg, players_data, events_config, output_file)
            print(f"  Generated {output_file}")
        except Exception as e:
            print(f"  Error generating {output_file}: {e}")

    # Generate index page
    print("Generating index.html...")
    generate_index_html(players_data, config)
    print("  Generated index.html")

    print("\nGeneration complete!")


if __name__ == "__main__":
    generate_all()
