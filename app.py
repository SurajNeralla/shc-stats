from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
from dotenv import load_dotenv
import os
from datetime import timedelta

load_dotenv()

from werkzeug.security import generate_password_hash, check_password_hash

from models import (
    supabase, get_players, get_player, create_player, update_player, 
    create_player_stats, update_player_stats, get_leaderboard_runs, get_leaderboard_wickets, 
    get_leaderboard_fours, get_leaderboard_sixes, get_leaderboard_ones, get_leaderboard_twos,
    delete_player,
    get_match_logs, add_match_log, delete_match_log, get_player_by_email,
    recalculate_player_stats
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-default")
app.permanent_session_lifetime = timedelta(days=30)

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
        player_allowed = ['my_stats', 'dashboard', 'roster', 'leaderboard', 'index', 'logout', 'api_player_stats']
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
        remember = request.form.get('remember') == 'on'
        
        if account_type == 'player':
            player = get_player_by_email(email)
            if player and player.get('password') and check_password_hash(player['password'], password):
                session.pop('admin_token', None)
                session.permanent = remember
                session['player_id'] = player['id']
                return redirect(url_for('my_stats'))
            else:
                flash("Invalid Player email or password.", "error")
        else:
            try:
                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                session.pop('player_id', None)
                session.permanent = remember
                session['admin_token'] = res.session.access_token
                return redirect(url_for('dashboard'))
            except Exception:
                flash("Invalid Admin email or password.", "error")
            
    return render_template('login.html')

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        session.pop('admin_token', None)
        session.pop('player_id', None)
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        return redirect(url_for('login'))
    return render_template('logout.html')

@app.route('/dashboard')
def dashboard():
    all_players = get_players()
    is_admin = 'admin_token' in session
    return render_template('dashboard.html', players=all_players, is_admin=is_admin)

@app.route('/roster')
def roster():
    search = request.args.get('search', '')
    all_players = get_players()
    if search:
        all_players = [p for p in all_players if search.lower() in p.get('name', '').lower()]
    
    is_admin = 'admin_token' in session
    # Calculate Milestones (Next hundred runs, Next 5 wickets)
    milestones = []
    for p in all_players:
        ps = p.get('player_stats', {}) if isinstance(p.get('player_stats'), dict) else (p.get('player_stats')[0] if p.get('player_stats') else {})
        runs = ps.get('runs', 0)
        wickets = ps.get('wickets', 0)
        
        # Runs Milestone
        next_run_milestone = ((runs // 100) + 1) * 100
        if next_run_milestone - runs <= 20 and runs > 0:
            milestones.append({'name': p['name'], 'type': 'runs', 'target': next_run_milestone, 'diff': next_run_milestone - runs})
            
        # Wickets Milestone
        next_wkt_milestone = ((wickets // 5) + 1) * 5
        if next_wkt_milestone - wickets <= 2 and wickets > 0:
            milestones.append({'name': p['name'], 'type': 'wickets', 'target': next_wkt_milestone, 'diff': next_wkt_milestone - wickets})

    # Fetch all logs for performance trend icons
    try:
        all_logs = supabase.table("match_logs").select("*").order("match_date", desc=True).limit(200).execute().data
    except:
        all_logs = []

    milestones.sort(key=lambda x: x['diff'])

    # Organize logs by player for the form guide
    player_forms = {}
    for l in all_logs:
        pid = str(l.get('player_id'))
        if pid not in player_forms:
            player_forms[pid] = []
        if len(player_forms[pid]) < 5:
            # Simple form logic: 🟢 (30+ runs / 1+ wkts), 🟡 (10-30 runs), 🔴 (otherwise)
            score = l.get('runs', 0)
            wkts = l.get('wickets', 0)
            if score >= 30 or wkts >= 1: status = 'good'
            elif score >= 10: status = 'average'
            else: status = 'low'
            player_forms[pid].append(status)

    return render_template('roster.html', 
                          players=all_players, 
                          search=search, 
                          is_admin=is_admin,
                          milestones=milestones[:5],
                          player_forms=player_forms)

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
            'not_out': request.form.get('not_out') == 'on',
            'runs': int(request.form.get('runs', 0)),
            'balls_faced': int(request.form.get('balls_faced', 0)),
            'ones': int(request.form.get('ones', 0)),
            'twos': int(request.form.get('twos', 0)),
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
    fours_leaders = get_leaderboard_fours()
    sixes_leaders = get_leaderboard_sixes()
    ones_leaders = get_leaderboard_ones()
    twos_leaders = get_leaderboard_twos()
    
    logged_in_player_id = session.get('player_id')
    return render_template('leaderboard.html', 
                           runs_leaders=runs_leaders, 
                           wickets_leaders=wickets_leaders,
                           fours_leaders=fours_leaders,
                           sixes_leaders=sixes_leaders,
                           ones_leaders=ones_leaders,
                           twos_leaders=twos_leaders,
                           logged_in_player_id=logged_in_player_id)


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

@app.route('/compare')
def compare_players_page():
    all_players = get_players()
    return render_template('compare.html', players=all_players)

@app.route('/api/player/<player_id>')
def api_player_stats(player_id):
    p = get_player(player_id)
    # Ensure stats are included and formatted correctly for the JS
    stats = p.get('player_stats')
    if isinstance(stats, list):
        p['player_stats'] = stats[0] if stats else {}
    elif isinstance(stats, dict):
        p['player_stats'] = stats
    else:
        p['player_stats'] = {}
    return jsonify(p)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
