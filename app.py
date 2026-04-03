from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from dotenv import load_dotenv
import os

load_dotenv()

from werkzeug.security import generate_password_hash, check_password_hash

from models import (
    supabase, get_players, get_player, create_player, update_player, 
    create_player_stats, update_player_stats, get_leaderboard_runs, get_leaderboard_wickets, delete_player,
    get_match_logs, add_match_log, delete_match_log, get_player_by_email,
    create_live_match, get_live_match, update_live_match, create_live_match_players,
    get_live_match_players, update_live_match_player, log_live_ball, sync_player_career_stats,
    get_all_live_matches, delete_live_match, undo_last_ball, get_completed_matches,
    recalculate_player_stats, get_live_match_ball_logs
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-default")

# Name → local static image map (used as fallback if DB image_url is empty)
_NAME_IMAGE_MAP = {
    'suraj':   '/static/images/suraj.jpg.jpeg',
    'sashank': '/static/images/sashank.jpeg',
    'saran':   '/static/images/saran.jpeg',
    'abhi':    '/static/images/abhi.jpeg',
    'deepu':   '/static/images/deepu.jpeg',
    'kl':      '/static/images/deepu.jpeg',
    'sunny':   '/static/images/sunny.jpeg',
    'pavan':   '/static/images/pavan.jpeg',
    'prabhas': '/static/images/prabhas.jpeg',
    'sailesh': '/static/images/sailesh.jpeg',
}

def player_image_url(name):
    """Return the best image path for a player — DB url if set, else map by name."""
    if not name:
        return ''
    lower = name.lower()
    from flask import url_for
    for key, path in _NAME_IMAGE_MAP.items():
        if key in lower:
            # path is e.g. /static/images/suraj.jpg.jpeg
            filename = path.replace('/static/', '')
            return url_for('static', filename=filename)
    return ''

app.jinja_env.globals['player_image_url'] = player_image_url



@app.route('/sw.js')
def serve_sw():
    return send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/manifest.json')
def serve_manifest():
    return send_from_directory('static', 'manifest.json', mimetype='application/manifest+json')

@app.before_request
def check_auth():
    public_routes = ['login', 'static', 'serve_sw', 'serve_manifest']
    if request.endpoint in public_routes:
        return

    if 'admin_token' not in session and 'player_id' not in session:
        return redirect(url_for('login'))

    if 'admin_token' not in session:
        player_allowed = ['my_stats', 'dashboard', 'leaderboard', 'match_history', 'index', 'logout']
        if request.endpoint not in player_allowed:
            return redirect(url_for('dashboard'))

@app.route('/')
def index():
    if 'player_id' in session:
        return redirect(url_for('my_stats'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        account_type = request.form.get('account_type', 'admin')
        
        if account_type == 'player':
            player = get_player_by_email(email)
            if player and player.get('password') and check_password_hash(player['password'], password):
                session.pop('admin_token', None)
                session['player_id'] = player['id']
                return redirect(url_for('my_stats'))
            else:
                flash("Invalid Player email or password.", "error")
        else:
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                session.pop('player_id', None)
                session['admin_token'] = res.session.access_token
                return redirect(url_for('dashboard'))
            except Exception:
                flash("Invalid Admin email or password.", "error")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_token', None)
    session.pop('player_id', None)
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    search = request.args.get('search', '')
    all_players = get_players()
    if search:
        all_players = [p for p in all_players if search.lower() in p.get('name', '').lower()]
    
    is_admin = 'admin_token' in session
    live_matches = get_all_live_matches() if is_admin else []
    
    return render_template('dashboard.html', players=all_players, search=search, is_admin=is_admin, live_matches=live_matches)

@app.route('/players/new', methods=['GET', 'POST'])
def new_player():
    if request.method == 'POST':
        player_data = {
            'name': request.form.get('name'),
            'age': int(request.form.get('age', 0) or 0),
            'team': request.form.get('team'),
            'role': request.form.get('role'),
            'image_url': request.form.get('image_url'),
            'email': request.form.get('email') or None
        }
        raw_password = request.form.get('password')
        if raw_password:
            player_data['password'] = generate_password_hash(raw_password)
        res = create_player(player_data)
        if res.data:
            player_id = res.data[0]['id']
            # Create an empty stats record
            create_player_stats({'player_id': player_id})
            return redirect(url_for('edit_player', player_id=player_id))
    return render_template('player_form.html', player=None)

@app.route('/players/<player_id>/edit', methods=['GET', 'POST'])
def edit_player(player_id):
    try:
        player_with_stats = get_player(player_id)
    except Exception as e:
        flash("Player not found.", "error")
        return redirect(url_for('dashboard'))

    stats = player_with_stats.get('player_stats')
    if isinstance(stats, list):
        stat = stats[0] if stats else {}
    elif isinstance(stats, dict):
        stat = stats
    else:
        stat = {}

    match_logs = get_match_logs(player_id)

    if request.method == 'POST':
        player_data = {
            'name': request.form.get('name'),
            'age': int(request.form.get('age', 0) or 0),
            'team': request.form.get('team'),
            'role': request.form.get('role'),
            'image_url': request.form.get('image_url'),
            'email': request.form.get('email') or None
        }
        raw_password = request.form.get('password')
        if raw_password:
            player_data['password'] = generate_password_hash(raw_password)
        
        update_player(player_id, player_data)
        flash("Player profile updated successfully!", "success")
        return redirect(url_for('edit_player', player_id=player_id))
    
    return render_template('player_form.html', player=player_with_stats, stats=stat, logs=match_logs)

@app.route('/players/<player_id>/matches/new', methods=['GET', 'POST'])
def add_match(player_id):
    if request.method == 'POST':
        match_data = {
            'match_date': request.form.get('match_date') or None,
            'opponent': request.form.get('opponent'),
            'runs': int(request.form.get('runs', 0)),
            'balls_faced': int(request.form.get('balls_faced', 0)),
            'fours': int(request.form.get('fours', 0)),
            'sixes': int(request.form.get('sixes', 0)),
            'overs_bowled': float(request.form.get('overs_bowled', 0)),
            'maidens': int(request.form.get('maidens', 0)),
            'runs_conceded': int(request.form.get('runs_conceded', 0)),
            'wickets': int(request.form.get('wickets', 0)),
            'no_balls': int(request.form.get('no_balls', 0)),
            'wides': int(request.form.get('wides', 0)),
            'catches': int(request.form.get('catches', 0)),
            'stumpings': int(request.form.get('stumpings', 0))
        }
        try:
            add_match_log(player_id, match_data)
            flash("Match log added and total stats recalculated successfully!", "success")
        except Exception as e:
            flash(f"Error adding match: {str(e)}", "error")
        return redirect(url_for('edit_player', player_id=player_id))
    
    player = get_player(player_id)
    return render_template('match_form.html', player=player)

@app.route('/players/<player_id>/matches/<log_id>/delete', methods=['POST'])
def remove_match(player_id, log_id):
    try:
        delete_match_log(log_id, player_id)
        flash("Match log deleted and totals recalculated successfully.", "success")
    except Exception as e:
        flash(f"Error deleting match log: {str(e)}", "error")
    return redirect(url_for('edit_player', player_id=player_id))

@app.route('/leaderboard')
def leaderboard():
    runs_leaders = get_leaderboard_runs()
    wickets_leaders = get_leaderboard_wickets()
    logged_in_player_id = session.get('player_id')
    return render_template('leaderboard.html', runs_leaders=runs_leaders, wickets_leaders=wickets_leaders, logged_in_player_id=logged_in_player_id)

@app.route('/history')
def match_history():
    matches = get_completed_matches()
    return render_template('match_history.html', matches=matches)

@app.route('/players/<player_id>/delete', methods=['POST'])
def remove_player(player_id):
    try:
        delete_player(player_id)
        flash("Player deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting player: {str(e)}", "error")
    return redirect(url_for('dashboard'))

@app.route('/my_stats')
def my_stats():
    player_id = session.get('player_id')
    if not player_id:
        return redirect(url_for('login'))
        
    player_with_stats = get_player(player_id)
    stats = player_with_stats.get('player_stats')
    if isinstance(stats, list):
        stat = stats[0] if stats else {}
    elif isinstance(stats, dict):
        stat = stats
    else:
        stat = {}
        
    match_logs = get_match_logs(player_id)
    return render_template('my_stats.html', player=player_with_stats, stats=stat, logs=match_logs)

# --- LIVE MATCH ROUTES ---

@app.route('/live-match/setup')
def live_match_setup():
    players = get_players()
    return render_template('live_match_setup.html', players=players)

@app.route('/api/live-match/init', methods=['POST'])
def init_live_match():
    # Only admins can init matches
    if 'admin_token' not in session:
        return {"error": "Unauthorized"}, 401

    data = request.json
    team_a_name = data.get('team_a_name')
    team_b_name = data.get('team_b_name')
    team_a_players = data.get('team_a_players', [])
    team_b_players = data.get('team_b_players', [])
    total_overs = data.get('total_overs', 20)

    if not (3 <= len(team_a_players) <= 11) or not (3 <= len(team_b_players) <= 11):
        return {"error": "Both teams must have between 3 and 11 players."}, 400

    match_res = create_live_match({
        "team_a_name": team_a_name,
        "team_b_name": team_b_name,
        "total_overs": total_overs,
        "status": "setup"
    })
    
    if not match_res.data:
        return {"error": "Failed to create match."}, 500

    match_id = match_res.data[0]['id']

    # Assign players
    player_inserts = []
    for pid in team_a_players:
        player_inserts.append({"live_match_id": match_id, "player_id": pid, "team": "team_a", "status": "waiting"})
    for pid in team_b_players:
        player_inserts.append({"live_match_id": match_id, "player_id": pid, "team": "team_b", "status": "waiting"})

    create_live_match_players(player_inserts)

    return {"match_id": match_id}, 200

@app.route('/live-match/<match_id>/toss')
def live_match_toss(match_id):
    match = get_live_match(match_id)
    if not match:
        flash("Match not found.", "error")
        return redirect(url_for('dashboard'))
    return render_template('live_match_toss.html', match=match)

@app.route('/api/live-match/<match_id>/toss', methods=['POST'])
def save_toss(match_id):
    if 'admin_token' not in session:
        return {"error": "Unauthorized"}, 401

    data = request.json
    toss_winner = data.get('toss_winner')
    toss_decision = data.get('toss_decision')

    # Update match
    update_live_match(match_id, {
        "toss_winner": toss_winner,
        "toss_decision": toss_decision,
        "status": "innings_1",
        "current_innings": 1
    })

    return {"success": True}, 200

@app.route('/live-match/<match_id>/scorecard')
def live_scorecard(match_id):
    match = get_live_match(match_id)
    if not match:
        return redirect(url_for('dashboard'))

    players = get_live_match_players(match_id)
    team_a = [p for p in players if p['team'] == 'team_a']
    team_b = [p for p in players if p['team'] == 'team_b']

    # Determine batting and bowling teams based on toss
    if (match['toss_winner'] == 'team_a' and match['toss_decision'] == 'bat') or (match['toss_winner'] == 'team_b' and match['toss_decision'] == 'bowl'):
        batting_team = 'team_a' if match['current_innings'] == 1 else 'team_b'
        bowling_team = 'team_b' if match['current_innings'] == 1 else 'team_a'
    else:
        batting_team = 'team_b' if match['current_innings'] == 1 else 'team_a'
        bowling_team = 'team_a' if match['current_innings'] == 1 else 'team_b'

    batting_players = team_a if batting_team == 'team_a' else team_b
    bowling_players = team_b if batting_team == 'team_a' else team_a
    
    striker = next((p for p in batting_players if p.get('is_striker')), None)
    non_striker = next((p for p in batting_players if p.get('is_non_striker')), None)
    bowler = next((p for p in bowling_players if p.get('is_current_bowler')), None)
    
    # Fetch recent balls for the "this over" tracker
    ball_logs = get_live_match_ball_logs(match_id)
    
    return render_template('live_scorecard.html', 
        match=match, 
        batting_team=batting_team, 
        batting_players=batting_players, 
        bowling_players=bowling_players,
        striker=striker,
        non_striker=non_striker,
        bowler=bowler,
        ball_logs=ball_logs
    )

@app.route('/api/debug/live-match/<match_id>/players')
def debug_players(match_id):
    players = get_live_match_players(match_id)
    return jsonify(players)

@app.route('/api/live-match/<match_id>/score', methods=['POST'])
def update_score(match_id):
    data = request.json
    event_type = data.get('type')
    
    # swap_batter and swap_bowler are selection events, allow any logged-in user
    # run/extra/wicket events require admin
    if event_type not in ('swap_batter', 'swap_bowler') and 'admin_token' not in session:
        return {"error": "Unauthorized"}, 401

    match = get_live_match(match_id)
    if not match:
        return {"error": "Match not found"}, 404

    # data already parsed above
    # event_type already set above
    
    # We will need the players list heavily
    players = get_live_match_players(match_id)
    
    # helper
    def get_lmp(lmp_id): return next((p for p in players if p['id'] == lmp_id), None)
    
    if event_type == 'swap_batter':
        # New batter comes in (data contains lmp_id)
        new_batter_id = data.get('new_batter_id')
        role = data.get('role', 'striker')
        p = get_lmp(new_batter_id)
        if p:
            if role == 'non_striker':
                update_live_match_player(p['id'], {'status': 'batting', 'is_striker': False, 'is_non_striker': True})
            else:
                update_live_match_player(p['id'], {'status': 'batting', 'is_striker': True, 'is_non_striker': False})
        return {"success": True}, 200
        
    if event_type == 'swap_bowler':
        # End of over: old bowler stops, new bowler starts (data contains lmp_ids)
        old_bowler_id = data.get('old_bowler_id')
        new_bowler_id = data.get('new_bowler_id')
        is_correction = data.get('is_correction', False)
        
        ob = get_lmp(old_bowler_id)
        if ob: update_live_match_player(ob['id'], {'is_current_bowler': False})
        
        nb = get_lmp(new_bowler_id)
        if nb: 
            bowling_team = nb['team']
            for p in players:
                if p['team'] == bowling_team and p['is_current_bowler'] and p['id'] != nb['id']:
                    update_live_match_player(p['id'], {'is_current_bowler': False})
            update_live_match_player(nb['id'], {'status': 'bowling', 'is_current_bowler': True})
        
        # At end of over, strikers swap
        if not is_correction:
            striker = next((p for p in players if p['is_striker']), None)
            non_striker = next((p for p in players if p['is_non_striker']), None)
            if striker and non_striker:
                update_live_match_player(striker['id'], {'is_striker': False, 'is_non_striker': True})
                update_live_match_player(non_striker['id'], {'is_striker': True, 'is_non_striker': False})
            
        return {"success": True}, 200

    striker = next((p for p in players if p['is_striker']), None)
    non_striker = next((p for p in players if p['is_non_striker']), None)
    bowler = next((p for p in players if p['is_current_bowler']), None)

    team_prefix = 'team_a' if match['current_innings'] == 1 and match['toss_winner'] == 'team_a' and match['toss_decision'] == 'bat' else 'team_b' # Simplified, actually need to just check striker's team
    if striker:
        team_prefix = striker['team']
        
    score_col = f"{team_prefix}_score"
    balls_col = f"{team_prefix}_balls"
    wickets_col = f"{team_prefix}_wickets"
    
    current_score = match.get(score_col, 0)
    current_balls = match.get(balls_col, 0)
    current_wickets = match.get(wickets_col, 0)

    is_legal_ball = True
    runs = data.get('runs', 0)
    
    if event_type == 'run':
        # Batch-update striker in one call
        s_runs = striker['runs_scored'] + runs
        s_balls = striker['balls_faced'] + 1
        s_fours = striker['fours'] + (1 if runs == 4 else 0)
        s_sixes = striker['sixes'] + (1 if runs == 6 else 0)
        striker_update = {'runs_scored': s_runs, 'balls_faced': s_balls, 'fours': s_fours, 'sixes': s_sixes}
        
        # Odd runs swap — fold into same update
        if runs % 2 != 0 and non_striker:
            striker_update['is_striker'] = False
            striker_update['is_non_striker'] = True
        update_live_match_player(striker['id'], striker_update)
        
        # Batch-update bowler in one call
        b_balls = bowler['balls_bowled'] + 1
        b_runs = bowler['runs_conceded'] + runs
        update_live_match_player(bowler['id'], {'balls_bowled': b_balls, 'runs_conceded': b_runs})
        
        if runs % 2 != 0 and non_striker:
            update_live_match_player(non_striker['id'], {'is_striker': True, 'is_non_striker': False})
        
        current_score += runs
        current_balls += 1
        
        log_live_ball(match_id, {
            'innings': match['current_innings'],
            'striker_id': striker['player_id'],
            'non_striker_id': non_striker['player_id'] if non_striker else None,
            'bowler_id': bowler['player_id'],
            'runs': runs,
            'extras': 0,
            'is_wicket': False
        })
        # Career stats deferred to match end — no per-ball sync

    elif event_type == 'extra':
        extra_type = data.get('extra_type') # wide, no-ball
        is_legal_ball = False
        current_score += 1 + runs # 1 for extra + runs off it
        
        # Update bowler — runs only, no legal ball counted
        b_runs = bowler['runs_conceded'] + 1 + runs
        update_live_match_player(bowler['id'], {'runs_conceded': b_runs})
        
        log_live_ball(match_id, {
            'innings': match['current_innings'],
            'striker_id': striker['player_id'] if striker else None,
            'non_striker_id': non_striker['player_id'] if non_striker else None,
            'bowler_id': bowler['player_id'],
            'runs': runs,
            'extras': 1,
            'extra_type': extra_type,
            'is_wicket': False
        })
        
        # No-ball with bat runs: credit to striker (no extra ball faced)
        if runs > 0 and extra_type == 'no-ball' and striker:
            s_runs = striker['runs_scored'] + runs
            update_live_match_player(striker['id'], {'runs_scored': s_runs})
        # Career stats deferred to match end — no per-ball sync

    elif event_type == 'wicket':
        current_balls += 1
        current_wickets += 1
        
        # Batch-update striker: mark out in one call
        s_balls = striker['balls_faced'] + 1
        update_live_match_player(striker['id'], {'balls_faced': s_balls, 'status': 'out', 'is_striker': False, 'is_non_striker': False})
        
        # Batch-update bowler in one call
        b_balls = bowler['balls_bowled'] + 1
        b_wickets = bowler['wickets_taken'] + 1
        update_live_match_player(bowler['id'], {'balls_bowled': b_balls, 'wickets_taken': b_wickets})
        
        log_live_ball(match_id, {
            'innings': match['current_innings'],
            'striker_id': striker['player_id'],
            'non_striker_id': non_striker['player_id'] if non_striker else None,
            'bowler_id': bowler['player_id'],
            'runs': 0,
            'extras': 0,
            'is_wicket': True
        })
        # Career stats deferred to match end — no per-ball sync

    # Innings end conditions
    is_innings_over = False
    match_won = False
    max_balls = match.get('total_overs', 20) * 6
    batting_team_count = len([p for p in players if p['team'] == team_prefix])
    
    if current_balls >= max_balls:
        is_innings_over = True
    # All players dismissed (single-batting mode: N wickets = innings over)
    if current_wickets >= batting_team_count:
        is_innings_over = True
        
    if match['current_innings'] == 2:
        target = match.get('target', 0)
        if current_score >= target and target > 0:
            is_innings_over = True
            match_won = True

    # Update Match
    update_live_match(match_id, {
        score_col: current_score,
        balls_col: current_balls,
        wickets_col: current_wickets
    })

    # Build response from in-memory data (avoid extra DB round-trip)
    # For wicket: striker is now out, return None so frontend knows to prompt new batter
    resp_striker = None
    resp_ns = None
    resp_bowler = None

    if event_type == 'wicket':
        # striker is out — frontend will open batter modal; return non-striker info only
        resp_ns = {"runs": non_striker['runs_scored'], "balls": non_striker['balls_faced']} if non_striker else None
        resp_bowler_final = {"balls": b_balls, "runs": bowler['runs_conceded'], "wickets": b_wickets}
    elif event_type == 'run':
        resp_striker = {"runs": s_runs, "balls": s_balls}
        resp_ns = {"runs": non_striker['runs_scored'], "balls": non_striker['balls_faced']} if non_striker else None
        resp_bowler_final = {"balls": b_balls, "runs": b_runs, "wickets": bowler['wickets_taken']}
    elif event_type == 'extra':
        resp_striker = {"runs": striker['runs_scored'] + (runs if runs > 0 and data.get('extra_type') == 'no-ball' else 0), "balls": striker['balls_faced']} if striker else None
        resp_ns = {"runs": non_striker['runs_scored'], "balls": non_striker['balls_faced']} if non_striker else None
        resp_bowler_final = {"balls": bowler['balls_bowled'], "runs": b_runs, "wickets": bowler['wickets_taken']}
    else:
        resp_bowler_final = {"balls": bowler['balls_bowled'], "runs": bowler['runs_conceded'], "wickets": bowler['wickets_taken']}

    return {
        "success": True,
        "end_of_over": (is_legal_ball and current_balls > 0 and current_balls % 6 == 0 and not is_innings_over),
        "innings_over": is_innings_over,
        "match_won": match_won,
        "is_wicket": (event_type == 'wicket'),
        "odd_runs": (event_type == 'run' and runs % 2 != 0),
        "striker": resp_striker,
        "non_striker": resp_ns,
        "bowler": resp_bowler_final,
        "match": {"score": current_score, "balls": current_balls, "wickets": current_wickets}
    }, 200

@app.route('/api/live-match/<match_id>/switch-innings', methods=['POST'])
def handle_switch_innings(match_id):
    if 'admin_token' not in session: return {"error": "Unauthorized"}, 401
    match = get_live_match(match_id)
    if not match: return {"error": "Match not found"}, 404
    
    target = max(match.get('team_a_score', 0), match.get('team_b_score', 0)) + 1
    update_live_match(match_id, {
        'current_innings': 2,
        'target': target,
        'status': 'innings_2'
    })
    
    # clear live states for next innings
    players = get_live_match_players(match_id)
    for p in players:
        if p['is_striker'] or p['is_non_striker'] or p['is_current_bowler']:
            update_live_match_player(p['id'], {'is_striker': False, 'is_non_striker': False, 'is_current_bowler': False})
            
    return {"success": True}, 200

@app.route('/api/live-match/<match_id>/undo', methods=['POST'])
def handle_undo_ball(match_id):
    if 'admin_token' not in session:
        return {"error": "Unauthorized"}, 401
    
    success = undo_last_ball(match_id)
    if not success:
        return {"error": "Could not undo last ball (maybe none exists)."}, 400
    return {"success": True}, 200

@app.route('/api/live-match/<match_id>/delete', methods=['POST'])
def handle_delete_match(match_id):
    if 'admin_token' not in session:
        return {"error": "Unauthorized"}, 401
    
    delete_live_match(match_id)
    flash("Match deleted successfully.", "success")
    return redirect(url_for('dashboard'))

@app.route('/api/live-match/<match_id>/end', methods=['POST'])
def handle_end_match(match_id):
    if 'admin_token' not in session:
        return {"error": "Unauthorized"}, 401
    
    match = get_live_match(match_id)
    if not match:
        return {"error": "Match not found"}, 404
        
    s_a = match.get('team_a_score', 0)
    s_b = match.get('team_b_score', 0)
    result = "Draw"
    if s_a > s_b: result = f"{match['team_a_name']} won"
    elif s_b > s_a: result = f"{match['team_b_name']} won"
    
    update_live_match(match_id, {'status': 'completed', 'match_result': result})
    
    # Recalculate career stats at the end of the match to save loading time during live play
    try:
        players = get_live_match_players(match_id)
        for p in players:
            sync_player_career_stats(p)
            recalculate_player_stats(p['player_id'])
    except Exception as e:
        print("Error recalculating stats on match end", e)
        
    return {"success": True, "result": result}, 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)
