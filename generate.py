import csv
from datetime import datetime
import os

def parse_number(value):
    if not value or value.strip() == '':
        return None
    try:
        return float(value.replace(",", "."))
    except:
        return None

def parse_date(value):
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except:
        return None

def get_proof_type(photo_val, link):
    """Determine proof type based on photo column and link"""
    if photo_val and photo_val.lower() == 'y':
        if 'youtube.com' in link or 'youtu.be' in link:
            return 'video'
        else:
            return 'photo'
    else:
        return 'claimed'

def format_proof_link(link, proof_type):
    """Format the proof link with appropriate text"""
    if proof_type == 'video':
        return f'<a href="{link}">Video</a>'
    elif proof_type == 'photo':
        return f'<a href="{link}">Photo</a>'
    else:
        return f'<a href="{link}">Claimed Only</a>'
        
def event_format_proof_link(link, proof_type):
    """Format the proof link with appropriate text"""
    if proof_type == 'video':
        return f'<a href="{link}">Video</a>'
    elif proof_type == 'photo':
        return f'<a href="{link}">Photo</a>'
    else:
        return f'<a href="{link}">Link</a>'

def leaderboard_analysis_with_html(file_path, score_col, date_col, link_col, course_name, output_html, html_style, lower_is_better=False):
    top_scores = []
    top3_changes = []
    
    # Track time in leaderboard - using dictionaries to track start dates
    first_place_periods = []  # List of (player, start_date, end_date)
    top23_periods = {}  # player -> [(start_date, end_date), ...] - ONLY positions 2 and 3
    
    current_top23_holders = {}  # player -> start_date for current positions 2 and 3
    current_first_holder = None
    current_first_start = None
    
    # Store all records for the record history table
    all_records = []
    record_improvements = []  # Store row numbers where top 3 improved
    
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        header = rows[0]
        
        # Parse all records first
        for i, row in enumerate(rows[1:], 1):  # Skip header
            if len(row) < max(score_col, date_col):
                continue
                
            record = {
                'row_num': i + 1,
                'player': row[0].strip(),
                'total_score': parse_number(row[score_col - 1]),
                'hurdle_dash': parse_number(row[2]) if len(row) > 2 else None,
                'pennant_capture': parse_number(row[3]) if len(row) > 3 else None,
                'relay_run': parse_number(row[4]) if len(row) > 4 else None,
                'bonus_points': parse_number(row[5]) if len(row) > 5 else None,
                'date': parse_date(row[date_col - 1]),
                'link': row[link_col - 1] if len(row) >= link_col else '',
                'country': row[8] if len(row) > 8 else '',
                'photo': row[9] if len(row) > 9 else 'n'
            }
            
            if record['total_score'] is None or record['date'] is None:
                continue
                
            all_records.append(record)
        
        # Now analyze leaderboard changes
        for record in all_records:
            score = record['total_score']
            date = record['date']
            name = record['player']
            row_num = record['row_num']
            
            # Store previous state
            previous_top3 = top_scores.copy()
            previous_first = top_scores[0] if top_scores else None
            
            # Update leaderboard
            top_scores.append((row_num, name, score, record))
            if lower_is_better:
                top_scores.sort(key=lambda x: (x[2], x[0]))
            else:
                top_scores.sort(key=lambda x: (-x[2], x[0]))
            top_scores = top_scores[:3]
            
            # Check if leaderboard changed
            if top_scores != previous_top3:
                # Get current positions 2 and 3 (excluding first place)
                new_top23_names = set(entry[1] for entry in top_scores[1:])  # Only positions 2 and 3
                
                # End periods for players no longer in positions 2-3
                for player, start_date in current_top23_holders.items():
                    if player not in new_top23_names:
                        # Player left positions 2-3
                        if player not in top23_periods:
                            top23_periods[player] = []
                        top23_periods[player].append((start_date, date))
                
                # End first place period if first place changed
                new_first = top_scores[0]
                if previous_first and new_first[1] != previous_first[1]:
                    # First place changed
                    if current_first_holder and current_first_start:
                        first_place_periods.append((current_first_holder, current_first_start, date))
                    current_first_holder = new_first[1]
                    current_first_start = date
                elif not previous_first:
                    # This is the very first record
                    current_first_holder = new_first[1]
                    current_first_start = date
                
                # Start new periods for players entering positions 2-3
                new_top23_holders = {}
                for entry in top_scores[1:]:  # Only check positions 2 and 3
                    player = entry[1]
                    if player in current_top23_holders:
                        # Player was already in positions 2-3, keep their start date
                        new_top23_holders[player] = current_top23_holders[player]
                    else:
                        # New player in positions 2-3
                        new_top23_holders[player] = date
                
                current_top23_holders = new_top23_holders
                
                # Store this as a record improvement
                record_improvements.append(row_num)
                top3_changes.append((row_num, [(n, s, r) for _, n, s, r in top_scores], date))
                
                print(f"\nAfter row {row_num} ({date}), new top 3:")
                for rank, (n, s, r) in enumerate(top3_changes[-1][1], start=1):
                    print(f"{rank}. {n} ({s})")
    
    # End final periods (use last date + 1 day or today's date)
    if all_records:
        final_date = all_records[-1]['date']
        
        # End remaining positions 2-3 periods
        for player, start_date in current_top23_holders.items():
            if player not in top23_periods:
                top23_periods[player] = []
            top23_periods[player].append((start_date, final_date))
        
        # End final first place period
        if current_first_holder and current_first_start:
            first_place_periods.append((current_first_holder, current_first_start, final_date))
    
    # Calculate total days
    first_holder_days = {}
    top23_presence_days = {}  # Renamed from top3_presence_days for clarity
    
    # Calculate first place days
    for player, start_date, end_date in first_place_periods:
        days = (end_date - start_date).days
        if days < 0:
            days = 0
        first_holder_days[player] = first_holder_days.get(player, 0) + days
    
    # Calculate positions 2-3 days
    for player, periods in top23_periods.items():
        total_days = 0
        for start_date, end_date in periods:
            days = (end_date - start_date).days
            if days < 0:
                days = 0
            total_days += days
        top23_presence_days[player] = total_days
    
    print(f"\n🔍 First place periods:")
    for player, start_date, end_date in first_place_periods:
        days = (end_date - start_date).days
        print(f"{player}: {start_date} to {end_date} ({days} days)")
    
    # Generate HTML based on chosen style
    if html_style == "simple":
        generate_simple_html(course_name, all_records, top3_changes, first_holder_days, top23_presence_days, output_html, lower_is_better=lower_is_better)
    else:
        generate_advanced_html(course_name, all_records, top3_changes, first_holder_days, top23_presence_days, output_html)
    
    # CSV export removed - only HTML generation needed
    
    return record_improvements

def generate_simple_html(course_name, all_records, top3_changes, first_holder_days, top23_presence_days, output_file, lower_is_better=False):
    """Generate the simple HTML file (based on block-smash.html format)"""
    
    # Get current record (best depending on event rule)
    if all_records:
        current_record = (min if lower_is_better else max)(all_records, key=lambda x: x['total_score'])
    else:
        current_record = None
    
    # Get record history (only records that made top 3 improvements)
    record_history = []
    improvement_rows = set(row_num for row_num, _, _ in top3_changes)
    
    for record in all_records:
        if record['row_num'] in improvement_rows:
            record_history.append(record)
    
    # Generate HTML content matching block-smash.html structure
    html_content = f'''<!DOCTYPE html>
<html>
\t<head>
\t\t<title>{course_name} - Pokeathlon WRs</title>
\t\t<link rel="stylesheet" href="../style.css" />
\t\t<meta name="viewport" content="width=device-width, initial-scale=1.0" />
\t\t<link rel="icon" href="../championship-trophy.svg" type="image/svg+xml">
\t</head>
\t<body>
\t\t<button id="themeToggle" class="theme-toggle" aria-label="Toggle dark/light theme">🌙</button>
\t\t<nav><a href="../index.html">← Back to All Events</a></nav>

\t\t<h1>{course_name} WR</h1>

\t\t<h2>Current Record</h2>
\t\t<div class="table-wrapper">
\t\t\t<table>
\t\t\t\t<thead>
\t\t\t\t\t<tr>
\t\t\t\t\t\t<th>Score</th>
\t\t\t\t\t\t<th>Player</th>
\t\t\t\t\t\t<th>Date</th>
\t\t\t\t\t\t<th>Proof</th>
\t\t\t\t\t</tr>
\t\t\t\t</thead>
\t\t\t\t<tbody>'''
    
    # Current Record section
    if current_record:
        proof_type = get_proof_type(current_record['photo'], current_record['link'])
        proof_link = event_format_proof_link(current_record['link'], proof_type)
        
        html_content += f'''
\t\t\t\t\t<tr>
\t\t\t\t\t\t<td>{current_record['total_score']}</td>
\t\t\t\t\t\t<td>{current_record['player']}</td>
\t\t\t\t\t\t<td>{current_record['date'].strftime("%Y-%m-%d")}</td>
\t\t\t\t\t\t<td>{proof_link}</td>
\t\t\t\t\t</tr>'''
    
    html_content += '''
\t\t\t\t</tbody>
\t\t\t</table>
\t\t</div>

\t\t<h2>Record History</h2>
\t\t<div class="table-wrapper">
\t\t\t<table>
\t\t\t\t<thead>
\t\t\t\t\t<tr>
\t\t\t\t\t\t<th>Player</th>
\t\t\t\t\t\t<th>Total Score</th>
\t\t\t\t\t\t<th>Date</th>
\t\t\t\t\t\t<th>Proof</th>
\t\t\t\t\t</tr>
\t\t\t\t</thead>
\t\t\t\t<tbody>'''
    
    # Record History section
    for record in record_history:
        proof_type = get_proof_type(record['photo'], record['link'])
        proof_link = event_format_proof_link(record['link'], proof_type)
        
        html_content += f'''
\t\t\t\t\t<tr>
\t\t\t\t\t\t<td>{record['player']}</td>
\t\t\t\t\t\t<td>{record['total_score']}</td>
\t\t\t\t\t\t<td>{record['date'].strftime("%d/%m/%Y")}</td>
\t\t\t\t\t\t<td>{proof_link}</td>
\t\t\t\t\t</tr>'''
    
    html_content += '''
\t\t\t\t</tbody>
\t\t\t</table>
\t\t</div>

\t\t<h2>Leaderboard Statistics</h2>
\t\t<div class="table-wrapper">
\t\t\t<table>
\t\t\t\t<thead>
\t\t\t\t\t<tr>
\t\t\t\t\t\t<th>Name</th>
\t\t\t\t\t\t<th>Number of days at #1</th>
\t\t\t\t\t\t<th>Number of days in Top 3</th>
\t\t\t\t</tr>
\t\t\t\t</thead>
\t\t\t\t<tbody>'''
    
    # Leaderboard Statistics section
    all_names = set(first_holder_days.keys()) | set(top23_presence_days.keys())
    if all_names:
        # Sort by days in positions 2-3 (descending)
        for name in sorted(all_names, key=lambda n: -top23_presence_days.get(n, 0)):
            html_content += f'''
\t\t\t\t\t<tr>
\t\t\t\t\t\t<td>{name}</td>
\t\t\t\t\t\t<td>{first_holder_days.get(name, 0)}</td>
\t\t\t\t\t\t<td>{top23_presence_days.get(name, 0)}</td>
\t\t\t\t\t</tr>'''
    
    html_content += '''
\t\t\t</tbody>
\t\t\t</table>
\t\t</div>
\t\t<script src="../js/tablesort.min.js"></script>
\t\t<script src="../js/tablesort.number.min.js"></script>
\t\t<script src="../js/tablesort.date.js"></script>
\t\t<script src="../js/theme-toggle.js"></script>
\t\t<script>
\t\t\tdocument.querySelectorAll('table').forEach(table => {
\t\t\t    const sort = new Tablesort(table);
\t\t\t});
\t\t</script>
\t</body>
</html>'''
    
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"\n✅ Simple HTML file generated: {output_file}")

def generate_advanced_html(course_name, all_records, top3_changes, first_holder_days, top23_presence_days, output_file):
    """Generate the advanced HTML file with filtering capabilities"""

    # Get current record (highest scoring record)
    current_record = max(all_records, key=lambda x: x['total_score']) if all_records else None

    # Get record history (only records that made top 3 improvements)
    record_history = []
    improvement_rows = set(row_num for row_num, _, _ in top3_changes)

    for record in all_records:
        if record['row_num'] in improvement_rows:
            record_history.append(record)

    # Generate HTML content
    html_content = f'''<!DOCTYPE html>
<html>
\t<head>
\t\t<title>{course_name} - Pokéathlon WRs</title>
\t\t<link rel="stylesheet" href="../style.css">
\t\t<meta name="viewport" content="width=device-width, initial-scale=1.0">
\t\t<link rel="icon" href="../championship-trophy.svg" type="image/svg+xml">
\t</head>
\t<body>
\t\t<button id="themeToggle" class="theme-toggle" aria-label="Toggle dark/light theme">🌙</button>
\t\t<nav><a href="../index.html">← Back to All Events</a></nav>

\t\t<h1>{course_name}</h1>

\t\t<div class="filter-container">
\t\t\t<h3>Filter by Proof Type</h3>
\t\t\t<div class="filter-options">
\t\t\t\t<div class="filter-option">
\t\t\t\t\t<input type="radio" id="all-record" name="proofFilter" value="all-record" checked>
\t\t\t\t\t<label for="all-record">ALL RECORDS</label>
\t\t\t</div>
\t\t\t\t<div class="filter-option">
\t\t\t\t\t<input type="radio" id="verified-record" name="proofFilter" value="verified-record">
\t\t\t\t\t<label for="verified-record">VERIFIED RECORD</label>
\t\t\t</div>
\t\t\t\t<div class="filter-option">
\t\t\t\t\t<input type="radio" id="photo" name="proofFilter" value="photo">
\t\t\t\t\t<label for="photo">PHOTO</label>
\t\t\t</div>
\t\t\t\t<div class="filter-option">
\t\t\t\t\t<input type="radio" id="video" name="proofFilter" value="video">
\t\t\t\t\t<label for="video">VIDEO</label>
\t\t\t</div>
\t\t\t\t<div class="filter-option">
\t\t\t\t\t<input type="radio" id="livestream" name="proofFilter" value="livestream">
\t\t\t\t\t<label for="livestream">LIVESTREAM</label>
\t\t\t</div>
\t\t</div>
\t\t\t<div class="filter-info">
\t\t\t\tChoose how strict you want the proof requirements to be.
\t\t\t</div>
\t\t</div>
\t\t<div class="stats" id="stats">
\t\t\tShowing verified records
\t\t</div>'''

    # Current Record section
    if current_record:
        proof_type = get_proof_type(current_record['photo'], current_record['link'])
        proof_link = format_proof_link(current_record['link'], proof_type)

        html_content += f'''
        
\t\t<h2>Current Record</h2>
\t\t<div class="table-wrapper">
\t\t<table>
\t\t\t<thead>
\t\t\t\t<tr>
\t\t\t\t\t<th>Player</th>
\t\t\t\t\t<th>Total Score</th>
\t\t\t\t\t<th>Hurdle Dash</th>
\t\t\t\t\t<th>Pennant Capture</th>
\t\t\t\t\t<th>Relay Run</th>
\t\t\t\t\t<th>Bonus Points</th>
\t\t\t\t\t<th>Date</th>
\t\t\t\t\t<th>Proof</th>
\t\t\t\t</tr>
\t\t\t</thead>
\t\t\t<tbody>
\t\t\t\t<tr data-proof="{proof_type}">
\t\t\t\t\t<td>{current_record['player']}</td>
\t\t\t\t\t<td>{int(current_record['total_score'])}</td>
\t\t\t\t\t<td>{int(current_record['hurdle_dash']) if current_record['hurdle_dash'] else '--'}</td>
\t\t\t\t\t<td>{int(current_record['pennant_capture']) if current_record['pennant_capture'] else '--'}</td>
\t\t\t\t\t<td>{int(current_record['relay_run']) if current_record['relay_run'] else '--'}</td>
\t\t\t\t\t<td>{int(current_record['bonus_points']) if current_record['bonus_points'] else '--'}</td>
\t\t\t\t\t<td>{current_record['date'].strftime("%d/%m/%Y")}</td>
\t\t\t\t\t<td>{proof_link}</td>
\t\t\t\t</tr>
\t\t\t</tbody>
\t\t</table>
\t\t</div>'''

    # Record History section
    html_content += '''

\t\t<h2>Record History</h2>
\t\t<div class="table-wrapper">
\t\t<table>
\t\t\t<thead>
\t\t\t\t<tr>
\t\t\t\t\t<th>Player</th>
\t\t\t\t\t<th data-sort-method='number'>Total Score</th>
\t\t\t\t\t<th data-sort-method='number'>Hurdle Dash</th>
\t\t\t\t\t<th data-sort-method='number'>Pennant Capture</th>
\t\t\t\t\t<th data-sort-method='number'>Relay Run</th>
\t\t\t\t\t<th data-sort-method='number'>Bonus Points</th>
\t\t\t\t\t<th>Date</th>
\t\t\t\t\t<th>Proof</th>
\t\t\t\t</tr>
\t\t\t</thead>
\t\t\t<tbody>'''

    for record in record_history:
        proof_type = get_proof_type(record['photo'], record['link'])
        proof_link = format_proof_link(record['link'], proof_type)

        html_content += f'''
\t\t\t\t<tr data-proof="{proof_type}">
\t\t\t\t\t<td>{record['player']}</td>
\t\t\t\t\t<td>{int(record['total_score'])}</td>
\t\t\t\t\t<td>{int(record['hurdle_dash']) if record['hurdle_dash'] else '--'}</td>
\t\t\t\t\t<td>{int(record['pennant_capture']) if record['pennant_capture'] else '--'}</td>
\t\t\t\t\t<td>{int(record['relay_run']) if record['relay_run'] else '--'}</td>
\t\t\t\t\t<td>{int(record['bonus_points']) if record['bonus_points'] else '--'}</td>
\t\t\t\t\t<td>{record['date'].strftime("%d/%m/%Y")}</td>
\t\t\t\t\t<td>{proof_link}</td>
\t\t\t\t</tr>'''

    html_content += '''
\t\t\t</tbody>
\t\t</table>
\t\t</div>'''

    # Leaderboard Statistics section
    all_names = set(first_holder_days.keys()) | set(top23_presence_days.keys())
    if all_names:
        html_content += '''

\t\t<h2>Leaderboard Statistics</h2>
\t\t<div class="table-wrapper">
\t\t<table>
\t\t\t<thead>
\t\t\t\t<tr>
\t\t\t\t\t<th>Player</th>
\t\t\t\t\t<th data-sort-method='number'>Number of days at #1</th>
\t\t\t\t\t<th data-sort-method='number'>Number of days in Top 3 (positions 2-3)</th>
\t\t\t\t</tr>
\t\t\t</thead>
\t\t\t<tbody>'''

        # Sort by days in positions 2-3 (descending)
        for name in sorted(all_names, key=lambda n: -top23_presence_days.get(n, 0)):
            html_content += f'''
\t\t\t\t<tr>
\t\t\t\t\t<td>{name}</td>
\t\t\t\t\t<td>{first_holder_days.get(name, 0)}</td>
\t\t\t\t\t<td>{top23_presence_days.get(name, 0)}</td>
\t\t\t\t</tr>'''

        html_content += '''
\t\t\t</tbody>
\t\t</table>
\t\t</div>'''

    # Footer with JavaScript
    html_content += '''
\t\t<script src="../js/tablesort.min.js"></script>
\t\t<script src="../js/tablesort.number.min.js"></script>
\t\t<script src="../js/tablesort.date.js"></script>
\t\t<script src="../js/sorting-logic.js"></script>
\t\t<script src="../js/theme-toggle.js"></script>
\t\t<script>
\t\t\tdocument.querySelectorAll('table').forEach(table => {
\t\t\t\tconst sort = new Tablesort(table);
\t\t\t});
\t\t</script>
\t</body>
</html>'''

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"\n✅ Advanced HTML file generated: {output_file}")

# CSV export functions removed - not needed for HTML generation

def generate_index_html():
    """Generate the main index.html file with current world records"""
    print("🏠 Generating index.html with current world records...")
    
    # Get course world records
    course_records = {}
    course_configs = {
        'Speed': 'csv/Pokeathlon WRs - Speed_Course.csv',
        'Power': 'csv/Pokeathlon WRs - Power_Course.csv', 
        'Skill': 'csv/Pokeathlon WRs - Skill_Course.csv',
        'Stamina': 'csv/Pokeathlon WRs - Stamina_Course.csv',
        'Jump': 'csv/Pokeathlon WRs - Jump_Course.csv'
    }
    
    for course_name, csv_file in course_configs.items():
        if os.path.exists(csv_file):
            try:
                with open(csv_file, newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    if len(rows) > 1:  # Has data beyond header
                        # Find best score (highest total score)
                        best_record = None
                        best_score = -1
                        
                        for row in rows[1:]:  # Skip header
                            if len(row) >= 7:  # Ensure we have enough columns
                                try:
                                    total_score = parse_number(row[1])  # Column B (Total Score)
                                    if total_score and total_score > best_score:
                                        best_score = total_score
                                        best_record = {
                                            'player': row[0].strip(),
                                            'total_score': int(total_score),
                                            'event1': int(parse_number(row[2])) if parse_number(row[2]) else '--',
                                            'event2': int(parse_number(row[3])) if parse_number(row[3]) else '--',
                                            'event3': int(parse_number(row[4])) if parse_number(row[4]) else '--',
                                            'bonus': int(parse_number(row[5])) if parse_number(row[5]) else '--',
                                            'date': parse_date(row[6])  # Column G (Date)
                                        }
                                except (ValueError, IndexError):
                                    continue
                        
                        if best_record:
                            course_records[course_name] = best_record
            except Exception as e:
                print(f"⚠️ Warning: Could not read {csv_file}: {e}")
    
    # Get event world records
    event_records = {}
    event_configs = {
        'Hurdle Dash': {'score_col': 2, 'lower_is_better': True},
        'Pennant Capture': {'score_col': 3, 'lower_is_better': False},
        'Circle Push': {'score_col': 4, 'lower_is_better': False},
        'Block Smash': {'score_col': 5, 'lower_is_better': False},
        'Disc Catch': {'score_col': 6, 'lower_is_better': False},
        'Lamp Jump': {'score_col': 7, 'lower_is_better': False},
        'Relay Run': {'score_col': 8, 'lower_is_better': False},
        'Ring Drop': {'score_col': 9, 'lower_is_better': False},
        'Snow Throw': {'score_col': 10, 'lower_is_better': False},
        'Goal Roll': {'score_col': 11, 'lower_is_better': False}
    }
    
    events_csv = 'csv/Pokeathlon WRs - Events_best_scores.csv'
    if os.path.exists(events_csv):
        try:
            with open(events_csv, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                if len(rows) > 1:  # Has data beyond header
                    for event_name, config in event_configs.items():
                        best_record = None
                        best_score = None
                        
                        for row in rows[1:]:  # Skip header
                            if len(row) >= 13:  # Ensure we have enough columns
                                try:
                                    score = parse_number(row[config['score_col'] - 1])
                                    if score is not None:
                                        if best_score is None:
                                            best_score = score
                                            best_record = {
                                                'player': row[0].strip(),
                                                'score': score,
                                                'points': int(parse_number(row[config['score_col'] - 1])) if not config['lower_is_better'] else int(parse_number(row[config['score_col'] - 1])),
                                                'date': parse_date(row[11])  # Column L (Date)
                                            }
                                        elif config['lower_is_better']:
                                            if score < best_score:
                                                best_score = score
                                                best_record = {
                                                    'player': row[0].strip(),
                                                    'score': score,
                                                    'points': int(parse_number(row[config['score_col'] - 1])),
                                                    'date': parse_date(row[11])
                                                }
                                        else:
                                            if score > best_score:
                                                best_score = score
                                                best_record = {
                                                    'player': row[0].strip(),
                                                    'score': score,
                                                    'points': int(parse_number(row[config['score_col'] - 1])),
                                                    'date': parse_date(row[11])
                                                }
                                except (ValueError, IndexError):
                                    continue
                        
                        if best_record:
                            event_records[event_name] = best_record
        except Exception as e:
            print(f"⚠️ Warning: Could not read {events_csv}: {e}")
    
    # Generate the index.html content
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
    </ul>
  </div>

  <h1>Pokeathlon World Records</h1>
  <p>Since the release of HG/SS, Pokeathlon has been an endless source of entertainment for many people. During these years people have shared their PBs in many different forums and websites, our goal is to create the go-to place for pokeathlon enjoyers.</p>
  
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
    
    # Add course records
    for course_name in ['Speed', 'Power', 'Skill', 'Stamina', 'Jump']:
        if course_name in course_records:
            record = course_records[course_name]
            html_content += f'''
        <tr>
          <td><a href="courses/{course_name.lower()}.html">{course_name}</a></td>
          <td>{record['player']}</td>
          <td>{record['total_score']}</td>
          <td>{record['event1']}</td>
          <td>{record['event2']}</td>
          <td>{record['event3']}</td>
          <td>{record['bonus']}</td>
          <td>{record['date'].strftime("%d/%m/%Y") if record['date'] else '--'}</td>
        </tr>'''
        else:
            html_content += f'''
        <tr>
          <td><a href="courses/{course_name.lower()}.html">{course_name}</a></td>
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
    
    # Add event records with formulas
    event_formulas = {
        'Hurdle Dash': r'\( \left\lfloor \frac{11500}{\text{score}} \right\rfloor \)',
        'Pennant Capture': r'\( \text{score} \times 3 \)',
        'Circle Push': r'\( \text{score} \times 3 \)',
        'Block Smash': r'\( \text{score} \)',
        'Disc Catch': r'\( 150 - \frac{1500}{\text{score} + 12.5} \)',
        'Lamp Jump': r'\( \left\lfloor \frac{\text{score}}{3.5} \right\rfloor \)',
        'Relay Run': r'\( \text{score} \times 10 \)',
        'Ring Drop': r'\( \text{score} \times 1.5 \)',
        'Snow Throw': r'\( \text{score} \times 3 \)',
        'Goal Roll': r'\( \text{position_points} + \text{score} \times 5 \)'
    }
    
    for event_name in ['Hurdle Dash', 'Pennant Capture', 'Circle Push', 'Block Smash', 'Disc Catch', 'Lamp Jump', 'Relay Run', 'Ring Drop', 'Snow Throw', 'Goal Roll']:
        if event_name in event_records:
            record = event_records[event_name]
            # Format score based on event type
            if event_name in ['Hurdle Dash', 'Relay Run']:
                score_display = f"{record['score']:.1f}".replace('.', ',')
            else:
                score_display = str(int(record['score'])) if record['score'] == int(record['score']) else str(record['score'])
            
            html_content += f'''
        <tr>
          <td><a href="events/{event_name.lower().replace(' ', '-')}.html">{event_name}</a></td>
          <td>{record['player']}</td>
          <td>{score_display}</td>
          <td>{record['points']}</td>
          <td>{event_formulas[event_name]}</td>
          <td>{record['date'].strftime("%d/%m/%Y") if record['date'] else '--'}</td>
        </tr>'''
        else:
            html_content += f'''
        <tr>
          <td>{event_name}</td>
          <td>–</td>
          <td>–</td>
          <td>–</td>
          <td>{event_formulas.get(event_name, '–')}</td>
          <td>–</td>
        </tr>'''
    
    html_content += '''
      </tbody>
    </table>
  </div>

  <p>Position points: 100-80-70-60.</p>

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
    
    # Write to file
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ index.html generated with current world records")
    print(f"   - {len(course_records)} course records")
    print(f"   - {len(event_records)} event records")

def generate_all_courses():
    """Generate HTML files for all courses automatically"""
    print("🏆 Pokéathlon Course HTML Generator - Auto Mode")
    print("=" * 50)
    
    # Define all courses with their configurations
    courses_config = {
        'Speed Course': {
            'csv_file': 'csv/Pokeathlon WRs - Speed_Course.csv',
            'score_col': 2,  # Column B (Total Score)
            'date_col': 7,   # Column G (Date)
            'link_col': 8,   # Column H (Link)
            'output_file': 'courses/speed.html',
            'lower_is_better': False  # Higher score is better for courses
        },
        'Jump Course': {
            'csv_file': 'csv/Pokeathlon WRs - Jump_Course.csv',
            'score_col': 2,  # Column B (Total Score)
            'date_col': 7,   # Column G (Date)
            'link_col': 8,   # Column H (Link)
            'output_file': 'courses/jump.html',
            'lower_is_better': False
        },
        'Power Course': {
            'csv_file': 'csv/Pokeathlon WRs - Power_Course.csv',
            'score_col': 2,  # Column B (Total Score)
            'date_col': 7,   # Column G (Date)
            'link_col': 8,   # Column H (Link)
            'output_file': 'courses/power.html',
            'lower_is_better': False
        },
        'Skill Course': {
            'csv_file': 'csv/Pokeathlon WRs - Skill_Course.csv',
            'score_col': 2,  # Column B (Total Score)
            'date_col': 7,   # Column G (Date)
            'link_col': 8,   # Column H (Link)
            'output_file': 'courses/skill.html',
            'lower_is_better': False
        },
        'Stamina Course': {
            'csv_file': 'csv/Pokeathlon WRs - Stamina_Course.csv',
            'score_col': 2,  # Column B (Total Score)
            'date_col': 7,   # Column G (Date)
            'link_col': 8,   # Column H (Link)
            'output_file': 'courses/stamina.html',
            'lower_is_better': False
        }
    }
    
    print(f"📊 Processing {len(courses_config)} courses...")
    print()
    
    total_improvements = 0
    
    for course_name, config in courses_config.items():
        print(f"🔄 Processing {course_name}...")
        
        csv_file = config['csv_file']
        if not os.path.exists(csv_file):
            print(f"❌ File '{csv_file}' not found! Skipping...")
            continue
        
        try:
            # Run the analysis and generate HTML
            improved_rows = leaderboard_analysis_with_html(
                csv_file, 
                config['score_col'], 
                config['date_col'], 
                config['link_col'], 
                course_name, 
                config['output_file'], 
                "advanced",  # Use advanced HTML style for courses
                lower_is_better=config.get('lower_is_better', False)
            )
            
            total_improvements += len(improved_rows)
            print(f"✅ {course_name}: {len(improved_rows)} improvements, HTML generated")
            
        except Exception as e:
            print(f"❌ Error processing {course_name}: {str(e)}")
        
        print()
    
    print(f"🎯 Course Summary:")
    print(f"- Processed {len(courses_config)} courses")
    print(f"- Total improvements found: {total_improvements}")
    print(f"- All HTML files generated in the 'courses' folder")

def generate_all_events():
    """Generate HTML files for all events automatically"""
    print("🏆 Pokéathlon HTML Generator - Auto Mode")
    print("=" * 50)
    
    # Define all events with their configurations
    events_config = {
        'Hurdle Dash': {
            'score_col': 2,  # Column B (Hurdle Dash)
            'date_col': 12,  # Column L (Date)
            'link_col': 13,  # Column M (Link)
            'output_file': 'events/hurdle-dash.html',
            'lower_is_better': True
        },
        'Pennant Capture': {
            'score_col': 3,  # Column C (Pennant Capture)
            'date_col': 12,  # Column L (Date)
            'link_col': 13,  # Column M (Link)
            'output_file': 'events/pennant-capture.html'
        },
        'Circle Push': {
            'score_col': 4,  # Column D (Circle Push)
            'date_col': 12,  # Column L (Date)
            'link_col': 13,  # Column M (Link)
            'output_file': 'events/circle-push.html'
        },
        'Block Smash': {
            'score_col': 5,  # Column E (Block Smash)
            'date_col': 12,  # Column L (Date)
            'link_col': 13,  # Column M (Link)
            'output_file': 'events/block-smash.html'
        },
        'Disc Catch': {
            'score_col': 6,  # Column F (Disc Catch)
            'date_col': 12,  # Column L (Date)
            'link_col': 13,  # Column M (Link)
            'output_file': 'events/disc-catch.html'
        },
        'Lamp Jump': {
            'score_col': 7,  # Column G (Lamp Jump)
            'date_col': 12,  # Column L (Date)
            'link_col': 13,  # Column M (Link)
            'output_file': 'events/lamp-jump.html'
        },
        'Relay Run': {
            'score_col': 8,  # Column H (Relay Run)
            'date_col': 12,  # Column L (Date)
            'link_col': 13,  # Column M (Link)
            'output_file': 'events/relay-run.html'
        },
        'Ring Drop': {
            'score_col': 9,  # Column I (Ring Drop)
            'date_col': 12,  # Column L (Date)
            'link_col': 13,  # Column M (Link)
            'output_file': 'events/ring-drop.html'
        },
        'Snow Throw': {
            'score_col': 10,  # Column J (Snow Throw)
            'date_col': 12,  # Column L (Date)
            'link_col': 13,  # Column M (Link)
            'output_file': 'events/snow-throw.html'
        },
        'Goal Roll': {
            'score_col': 11,  # Column K (Goal Roll)
            'date_col': 12,  # Column L (Date)
            'link_col': 13,  # Column M (Link)
            'output_file': 'events/goal-roll.html'
        }
    }
    
    csv_file = 'csv/Pokeathlon WRs - Events_best_scores.csv'
    
    if not os.path.exists(csv_file):
        print(f"❌ File '{csv_file}' not found!")
        return
    
    print(f"📊 Processing {len(events_config)} events from {csv_file}...")
    print()
    
    total_improvements = 0
    
    for event_name, config in events_config.items():
        print(f"🔄 Processing {event_name}...")
        
        try:
            # Run the analysis and generate HTML
            improved_rows = leaderboard_analysis_with_html(
                csv_file, 
                config['score_col'], 
                config['date_col'], 
                config['link_col'], 
                event_name, 
                config['output_file'], 
                "simple",  # Use simple HTML style for events
                lower_is_better=config.get('lower_is_better', False)
            )
            
            total_improvements += len(improved_rows)
            print(f"✅ {event_name}: {len(improved_rows)} improvements, HTML generated")
            
        except Exception as e:
            print(f"❌ Error processing {event_name}: {str(e)}")
        
        print()
    
    print(f"🎯 Events Summary:")
    print(f"- Processed {len(events_config)} events")
    print(f"- Total improvements found: {total_improvements}")
    print(f"- All HTML files generated in the 'events' folder")

def generate_all():
    """Generate HTML files for all events and courses"""
    print("🏆 Pokéathlon Complete HTML Generator")
    print("=" * 60)
    
    # Generate events first
    print("\n📋 GENERATING EVENTS...")
    generate_all_events()
    
    print("\n" + "=" * 60)
    
    # Generate courses
    print("\n📋 GENERATING COURSES...")
    generate_all_courses()
    
    print("\n" + "=" * 60)
    
    # Generate index.html
    print("\n📋 GENERATING INDEX.HTML...")
    generate_index_html()
    
    print("\n" + "=" * 60)
    print("🎉 All HTML generation complete!")

# Main execution
if __name__ == "__main__":
    # Auto-generate all events and courses
    generate_all()