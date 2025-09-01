import csv
from datetime import datetime
import os

def parse_number(value):
    """Parse a number from string, handling commas and empty values"""
    if not value or value.strip() == '':
        return None
    try:
        return float(value.replace(",", "."))
    except:
        return None

def parse_date(value):
    """Parse a date from DD/MM/YYYY format"""
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except:
        return None

def get_proof_type(photo_val, link):
    """Determine proof type based on photo column and link"""
    if photo_val and photo_val.lower() == 'y':
        return 'video' if ('youtube.com' in link or 'youtu.be' in link) else 'photo'
    return 'claimed'

def format_proof_link(link, proof_type, is_event=False):
    """Format the proof link with appropriate text"""
    if proof_type == 'video':
        return f'<a href="{link}">Video</a>'
    elif proof_type == 'photo':
        return f'<a href="{link}">Photo</a>'
    else:
        return f'<a href="{link}">{"Link" if is_event else "Claimed Only"}</a>'

def analyze_leaderboard(file_path, score_col, date_col, link_col, lower_is_better=False, 
                       event1_col=None, event2_col=None, event3_col=None, bonus_col=None):
    """Analyze leaderboard changes and return statistics"""
    top_scores = []
    top3_changes = []
    first_place_periods = []
    top23_periods = {}
    current_top23_holders = {}
    current_first_holder = None
    current_first_start = None
    all_records = []
    record_improvements = []
    
    with open(file_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        # Parse all records
        for i, row in enumerate(rows[1:], 1):
            if len(row) < max(score_col, date_col):
                continue
                
            record = {
                'row_num': i + 1,
                'player': row[0].strip(),
                'total_score': parse_number(row[score_col - 1]),
                'event1': parse_number(row[event1_col - 1]) if event1_col and len(row) >= event1_col else None,
                'event2': parse_number(row[event2_col - 1]) if event2_col and len(row) >= event2_col else None,
                'event3': parse_number(row[event3_col - 1]) if event3_col and len(row) >= event3_col else None,
                'bonus_points': parse_number(row[bonus_col - 1]) if bonus_col and len(row) >= bonus_col else None,
                'date': parse_date(row[date_col - 1]),
                'link': row[link_col - 1] if len(row) >= link_col else '',
                'photo': row[9] if len(row) > 9 else 'n'
            }
            
            if record['total_score'] is None or record['date'] is None:
                continue
            all_records.append(record)
        
        # Analyze leaderboard changes
        for record in all_records:
            previous_top3 = top_scores.copy()
            previous_first = top_scores[0] if top_scores else None
            
            # Update leaderboard
            top_scores.append((record['row_num'], record['player'], record['total_score'], record))
            top_scores.sort(key=lambda x: (x[2] if lower_is_better else -x[2], x[0]))
            top_scores = top_scores[:3]
            
            # Check if leaderboard changed
            if top_scores != previous_top3:
                new_top23_names = set(entry[1] for entry in top_scores[1:])
                
                # End periods for players no longer in positions 2-3
                for player, start_date in current_top23_holders.items():
                    if player not in new_top23_names:
                        if player not in top23_periods:
                            top23_periods[player] = []
                        top23_periods[player].append((start_date, record['date']))
                
                # Handle first place changes
                new_first = top_scores[0]
                if previous_first and new_first[1] != previous_first[1]:
                    if current_first_holder and current_first_start:
                        first_place_periods.append((current_first_holder, current_first_start, record['date']))
                    current_first_holder = new_first[1]
                    current_first_start = record['date']
                elif not previous_first:
                    current_first_holder = new_first[1]
                    current_first_start = record['date']
                
                # Start new periods for players entering positions 2-3
                new_top23_holders = {}
                for entry in top_scores[1:]:
                    player = entry[1]
                    new_top23_holders[player] = current_top23_holders.get(player, record['date'])
                
                current_top23_holders = new_top23_holders
                record_improvements.append(record['row_num'])
                top3_changes.append((record['row_num'], [(n, s, r) for _, n, s, r in top_scores], record['date']))
    
    # End final periods
    if all_records:
        final_date = all_records[-1]['date']
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
    
    return all_records, top3_changes, first_holder_days, top23_presence_days, record_improvements

def generate_simple_html(course_name, all_records, top3_changes, first_holder_days, top23_presence_days, output_file, lower_is_better=False):
    """Generate simple HTML file for events"""
    current_record = (min if lower_is_better else max)(all_records, key=lambda x: x['total_score']) if all_records else None
    improvement_rows = set(row_num for row_num, _, _ in top3_changes)
    record_history = [r for r in all_records if r['row_num'] in improvement_rows]
    
    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>{course_name} - Pokeathlon WRs</title>
    <link rel="stylesheet" href="../style.css" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" href="../championship-trophy.svg" type="image/svg+xml">
</head>
<body>
    <button id="themeToggle" class="theme-toggle" aria-label="Toggle dark/light theme">🌙</button>
    <nav><a href="../index.html">← Back to All Events</a></nav>

    <h1>{course_name} WR</h1>

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
        proof_type = get_proof_type(current_record['photo'], current_record['link'])
        proof_link = format_proof_link(current_record['link'], proof_type, is_event=True)
        html_content += f'''
                <tr>
                    <td>{current_record['total_score']}</td>
                    <td>{current_record['player']}</td>
                    <td>{current_record['date'].strftime("%Y-%m-%d")}</td>
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
        proof_type = get_proof_type(record['photo'], record['link'])
        proof_link = format_proof_link(record['link'], proof_type, is_event=True)
        html_content += f'''
                <tr>
                    <td>{record['player']}</td>
                    <td>{record['total_score']}</td>
                    <td>{record['date'].strftime("%d/%m/%Y")}</td>
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

def generate_advanced_html(course_name, all_records, top3_changes, first_holder_days, top23_presence_days, output_file, event1_name=None, event2_name=None, event3_name=None):
    """Generate advanced HTML file for courses with filtering"""
    current_record = max(all_records, key=lambda x: x['total_score']) if all_records else None
    improvement_rows = set(row_num for row_num, _, _ in top3_changes)
    record_history = [r for r in all_records if r['row_num'] in improvement_rows]

    html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>{course_name} - Pokéathlon WRs</title>
    <link rel="stylesheet" href="../style.css">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="../championship-trophy.svg" type="image/svg+xml">
</head>
<body>
    <button id="themeToggle" class="theme-toggle" aria-label="Toggle dark/light theme">🌙</button>
    <nav><a href="../index.html">← Back to All Events</a></nav>

    <h1>{course_name}</h1>

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
        proof_type = get_proof_type(current_record['photo'], current_record['link'])
        proof_link = format_proof_link(current_record['link'], proof_type)
        html_content += f'''
    
    <h2>Current Record</h2>
    <div class="table-wrapper">
    <table>
        <thead>
            <tr>
                <th>Player</th>
                <th>Total Score</th>
                <th>{event1_name or "Event 1"}</th>
                <th>{event2_name or "Event 2"}</th>
                <th>{event3_name or "Event 3"}</th>
                <th>Bonus Points</th>
                <th>Date</th>
                <th>Proof</th>
            </tr>
        </thead>
        <tbody>
            <tr data-proof="{proof_type}">
                <td>{current_record['player']}</td>
                <td>{int(current_record['total_score'])}</td>
                <td>{int(current_record['event1']) if current_record['event1'] else '--'}</td>
                <td>{int(current_record['event2']) if current_record['event2'] else '--'}</td>
                <td>{int(current_record['event3']) if current_record['event3'] else '--'}</td>
                <td>{int(current_record['bonus_points']) if current_record['bonus_points'] else '--'}</td>
                <td>{current_record['date'].strftime("%d/%m/%Y")}</td>
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
                <th data-sort-method='number'>{event1_name or "Event 1"}</th>
                <th data-sort-method='number'>{event2_name or "Event 2"}</th>
                <th data-sort-method='number'>{event3_name or "Event 3"}</th>
                <th data-sort-method='number'>Bonus Points</th>
                <th>Date</th>
                <th>Proof</th>
            </tr>
        </thead>
        <tbody>'''

    for record in record_history:
        proof_type = get_proof_type(record['photo'], record['link'])
        proof_link = format_proof_link(record['link'], proof_type)
        html_content += f'''
            <tr data-proof="{proof_type}">
                <td>{record['player']}</td>
                <td>{int(record['total_score'])}</td>
                <td>{int(record['event1']) if record['event1'] else '--'}</td>
                <td>{int(record['event2']) if record['event2'] else '--'}</td>
                <td>{int(record['event3']) if record['event3'] else '--'}</td>
                <td>{int(record['bonus_points']) if record['bonus_points'] else '--'}</td>
                <td>{record['date'].strftime("%d/%m/%Y")}</td>
                <td>{proof_link}</td>
            </tr>'''

    html_content += '''
        </tbody>
    </table>
    </div>'''

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

def generate_leaderboard_html(file_path, score_col, date_col, link_col, course_name, output_html, html_style, lower_is_better=False, event1_col=None, event2_col=None, event3_col=None, bonus_col=None, event1_name=None, event2_name=None, event3_name=None):
    """Main function to analyze leaderboard and generate HTML"""
    all_records, top3_changes, first_holder_days, top23_presence_days, record_improvements = analyze_leaderboard(
        file_path, score_col, date_col, link_col, lower_is_better, event1_col, event2_col, event3_col, bonus_col
    )
    
    if html_style == "simple":
        generate_simple_html(course_name, all_records, top3_changes, first_holder_days, top23_presence_days, output_html, lower_is_better)
    else:
        generate_advanced_html(course_name, all_records, top3_changes, first_holder_days, top23_presence_days, output_html, event1_name, event2_name, event3_name)
    
    return record_improvements

def get_course_records():
    """Get current world records for all courses"""
    course_configs = {
        'Speed': {'csv_file': 'csv/Pokeathlon WRs - Speed_Course.csv', 'event1_col': 3, 'event2_col': 4, 'event3_col': 5, 'bonus_col': 6},
        'Power': {'csv_file': 'csv/Pokeathlon WRs - Power_Course.csv', 'event1_col': 3, 'event2_col': 4, 'event3_col': 5, 'bonus_col': 6},
        'Skill': {'csv_file': 'csv/Pokeathlon WRs - Skill_Course.csv', 'event1_col': 3, 'event2_col': 4, 'event3_col': 5, 'bonus_col': 6},
        'Stamina': {'csv_file': 'csv/Pokeathlon WRs - Stamina_Course.csv', 'event1_col': 3, 'event2_col': 4, 'event3_col': 5, 'bonus_col': 6},
        'Jump': {'csv_file': 'csv/Pokeathlon WRs - Jump_Course.csv', 'event1_col': 3, 'event2_col': 4, 'event3_col': 5, 'bonus_col': 6}
    }
    
    course_records = {}
    for course_name, config in course_configs.items():
        csv_file = config['csv_file']
        if os.path.exists(csv_file):
            try:
                with open(csv_file, newline='', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    if len(rows) > 1:
                        best_record = None
                        best_score = -1
                        
                        for row in rows[1:]:
                            if len(row) >= 7:
                                try:
                                    total_score = parse_number(row[1])
                                    if total_score and total_score > best_score:
                                        best_score = total_score
                                        event1_score = parse_number(row[config['event1_col'] - 1])
                                        event2_score = parse_number(row[config['event2_col'] - 1])
                                        event3_score = parse_number(row[config['event3_col'] - 1])
                                        
                                        event1_points = int(event1_score) if event1_score else 0
                                        event2_points = int(event2_score) if event2_score else 0
                                        event3_points = int(event3_score) if event3_score else 0
                                        
                                        best_record = {
                                            'player': row[0].strip(),
                                            'total_score': int(total_score),
                                            'event1_points': event1_points if event1_points > 0 else '--',
                                            'event2_points': event2_points if event2_points > 0 else '--',
                                            'event3_points': event3_points if event3_points > 0 else '--',
                                            'bonus': int(parse_number(row[config['bonus_col'] - 1])) if parse_number(row[config['bonus_col'] - 1]) else '--',
                                            'date': parse_date(row[6])
                                        }
                                except (ValueError, IndexError):
                                    continue
                        
                        if best_record:
                            course_records[course_name] = best_record
            except Exception as e:
                print(f"Warning: Could not read {csv_file}: {e}")
    
    return course_records

def get_event_records():
    """Get current world records for all events"""
    event_configs = {
        'Hurdle Dash': {'score_col': 2, 'lower_is_better': True},
        'Pennant Capture': {'score_col': 3, 'lower_is_better': False},
        'Block Smash': {'score_col': 5, 'lower_is_better': False},
        'Disc Catch': {'score_col': 6, 'lower_is_better': False},
        'Lamp Jump': {'score_col': 7, 'lower_is_better': False},
        'Relay Run': {'score_col': 8, 'lower_is_better': False},
        'Snow Throw': {'score_col': 10, 'lower_is_better': False},
        'Goal Roll': {'score_col': 11, 'lower_is_better': False}
    }
    
    # Fixed values for events without pages
    event_records = {
        'Circle Push': {'player': '–', 'score': 66, 'points': 198, 'date': datetime.strptime('12/09/2009', '%d/%m/%Y').date()},
        'Ring Drop': {'player': '–', 'score': 200, 'points': 200, 'date': datetime.strptime('12/09/2009', '%d/%m/%Y').date()}
    }
    
    events_csv = 'csv/Pokeathlon WRs - Events_best_scores.csv'
    if os.path.exists(events_csv):
        try:
            with open(events_csv, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                if len(rows) > 1:
                    for event_name, config in event_configs.items():
                        best_record = None
                        best_score = None
                        
                        for row in rows[1:]:
                            if len(row) >= 13:
                                try:
                                    score = parse_number(row[config['score_col'] - 1])
                                    if score is not None:
                                        # Calculate points using formulas
                                        points_map = {
                                            'Hurdle Dash': lambda s: min(200, int(11500 / s)),
                                            'Pennant Capture': lambda s: min(200, int(s * 3)),
                                            'Circle Push': lambda s: min(200, int(s * 3)),
                                            'Block Smash': lambda s: min(200, int(s)),
                                            'Disc Catch': lambda s: min(200, int(150 - (1500 / (s + 12.5)))),
                                            'Lamp Jump': lambda s: min(200, int(s / 3.5)),
                                            'Relay Run': lambda s: min(200, int(s * 10)),
                                            'Ring Drop': lambda s: min(200, int(s * 1.5)),
                                            'Snow Throw': lambda s: min(200, int(s * 3)),
                                            'Goal Roll': lambda s: min(200, int(100 + 5 * s))
                                        }
                                        
                                        points = points_map.get(event_name, lambda s: min(200, int(s)))(score)
                                        
                                        if best_score is None:
                                            best_score = score
                                            best_record = {'player': row[0].strip(), 'score': score, 'points': points, 'date': parse_date(row[11])}
                                        elif config['lower_is_better']:
                                            if score < best_score:
                                                best_score = score
                                                best_record = {'player': row[0].strip(), 'score': score, 'points': points, 'date': parse_date(row[11])}
                                        else:
                                            if score > best_score:
                                                best_score = score
                                                best_record = {'player': row[0].strip(), 'score': score, 'points': points, 'date': parse_date(row[11])}
                                except (ValueError, IndexError):
                                    continue
                        
                        if best_record:
                            event_records[event_name] = best_record
        except Exception as e:
            print(f"Warning: Could not read {events_csv}: {e}")
    
    return event_records

def generate_index_html():
    """Generate the main index.html file"""
    course_records = get_course_records()
    event_records = get_event_records()
    
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
    
    for course_name in ['Speed', 'Power', 'Skill', 'Stamina', 'Jump']:
        if course_name in course_records:
            record = course_records[course_name]
            html_content += f'''
        <tr>
          <td><a href="courses/{course_name.lower()}.html">{course_name}</a></td>
          <td>{record['player']}</td>
          <td>{record['total_score']}</td>
          <td>{record['event1_points']}</td>
          <td>{record['event2_points']}</td>
          <td>{record['event3_points']}</td>
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
    
    for event_name in ['Hurdle Dash', 'Pennant Capture', 'Circle Push', 'Block Smash', 'Disc Catch', 'Lamp Jump', 'Relay Run', 'Ring Drop', 'Snow Throw', 'Goal Roll']:
        if event_name in event_records:
            record = event_records[event_name]
            if event_name in ['Hurdle Dash', 'Relay Run']:
                score_display = f"{record['score']:.1f}".replace('.', ',')
            else:
                score_display = str(int(record['score'])) if record['score'] == int(record['score']) else str(record['score'])
            
            if event_name in ['Circle Push', 'Ring Drop']:
                event_cell = f'<td>{event_name}</td>'
            else:
                event_cell = f'<td><a href="events/{event_name.lower().replace(' ', '-')}.html">{event_name}</a></td>'
            
            html_content += f'''
        <tr>
          {event_cell}
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
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)

def generate_all():
    """Generate all HTML files"""
    # Course configurations
    courses_config = {
        'Speed Course': {
            'csv_file': 'csv/Pokeathlon WRs - Speed_Course.csv',
            'score_col': 2, 'date_col': 7, 'link_col': 8, 'output_file': 'courses/speed.html',
            'event1_col': 3, 'event2_col': 4, 'event3_col': 5, 'bonus_col': 6,
            'event1_name': 'Hurdle Dash', 'event2_name': 'Pennant Capture', 'event3_name': 'Relay Run'
        },
        'Jump Course': {
            'csv_file': 'csv/Pokeathlon WRs - Jump_Course.csv',
            'score_col': 2, 'date_col': 7, 'link_col': 8, 'output_file': 'courses/jump.html',
            'event1_col': 3, 'event2_col': 4, 'event3_col': 5, 'bonus_col': 6,
            'event1_name': 'Lamp Jump', 'event2_name': 'Disc Catch', 'event3_name': 'Hurdle Dash'
        },
        'Power Course': {
            'csv_file': 'csv/Pokeathlon WRs - Power_Course.csv',
            'score_col': 2, 'date_col': 7, 'link_col': 8, 'output_file': 'courses/power.html',
            'event1_col': 3, 'event2_col': 4, 'event3_col': 5, 'bonus_col': 6,
            'event1_name': 'Block Smash', 'event2_name': 'Circle Push', 'event3_name': 'Goal Roll'
        },
        'Skill Course': {
            'csv_file': 'csv/Pokeathlon WRs - Skill_Course.csv',
            'score_col': 2, 'date_col': 7, 'link_col': 8, 'output_file': 'courses/skill.html',
            'event1_col': 3, 'event2_col': 4, 'event3_col': 5, 'bonus_col': 6,
            'event1_name': 'Snow Throw', 'event2_name': 'Goal Roll', 'event3_name': 'Pennant Capture'
        },
        'Stamina Course': {
            'csv_file': 'csv/Pokeathlon WRs - Stamina_Course.csv',
            'score_col': 2, 'date_col': 7, 'link_col': 8, 'output_file': 'courses/stamina.html',
            'event1_col': 3, 'event2_col': 4, 'event3_col': 5, 'bonus_col': 6,
            'event1_name': 'Ring Drop', 'event2_name': 'Relay Run', 'event3_name': 'Block Smash'
        }
    }
    
    # Event configurations
    events_config = {
        'Hurdle Dash': {'score_col': 2, 'date_col': 12, 'link_col': 13, 'output_file': 'events/hurdle-dash.html', 'lower_is_better': True},
        'Pennant Capture': {'score_col': 3, 'date_col': 12, 'link_col': 13, 'output_file': 'events/pennant-capture.html'},
        'Block Smash': {'score_col': 5, 'date_col': 12, 'link_col': 13, 'output_file': 'events/block-smash.html'},
        'Disc Catch': {'score_col': 6, 'date_col': 12, 'link_col': 13, 'output_file': 'events/disc-catch.html'},
        'Lamp Jump': {'score_col': 7, 'date_col': 12, 'link_col': 13, 'output_file': 'events/lamp-jump.html'},
        'Relay Run': {'score_col': 8, 'date_col': 12, 'link_col': 13, 'output_file': 'events/relay-run.html'},
        'Snow Throw': {'score_col': 10, 'date_col': 12, 'link_col': 13, 'output_file': 'events/snow-throw.html'},
        'Goal Roll': {'score_col': 11, 'date_col': 12, 'link_col': 13, 'output_file': 'events/goal-roll.html'}
    }
    
    # Generate events
    events_csv = 'csv/Pokeathlon WRs - Events_best_scores.csv'
    if os.path.exists(events_csv):
        for event_name, config in events_config.items():
            try:
                generate_leaderboard_html(
                    events_csv, config['score_col'], config['date_col'], config['link_col'],
                    event_name, config['output_file'], "simple", config.get('lower_is_better', False)
                )
            except Exception as e:
                print(f"Error processing {event_name}: {e}")
    
    # Generate courses
    for course_name, config in courses_config.items():
        if os.path.exists(config['csv_file']):
            try:
                generate_leaderboard_html(
                    config['csv_file'], config['score_col'], config['date_col'], config['link_col'],
                    course_name, config['output_file'], "advanced", False,
                    config['event1_col'], config['event2_col'], config['event3_col'], config['bonus_col'],
                    config['event1_name'], config['event2_name'], config['event3_name']
                )
            except Exception as e:
                print(f"Error processing {course_name}: {e}")
    
    # Generate index.html
    generate_index_html()

if __name__ == "__main__":
    generate_all()