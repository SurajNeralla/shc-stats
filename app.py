from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from dotenv import load_dotenv
import os

load_dotenv()

from werkzeug.security import generate_password_hash, check_password_hash

from models import (
    supabase, get_players, get_player, create_player, update_player, 
    create_player_stats, update_player_stats, get_leaderboard_runs, get_leaderboard_wickets, delete_player,
    get_match_logs, add_match_log, delete_match_log, get_player_by_email,
    # New Fantasy Features
    create_premium_match, get_fantasy_leaderboard, get_match_history
)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-default")

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
        player_allowed = ['my_stats', 'dashboard', 'leaderboard', 'index', 'logout', 'fantasy', 'fantasy_history']
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
    return render_template('dashboard.html', players=all_players, search=search, is_admin=is_admin)

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
    return render_template('leaderboard.html', runs_leaders=runs_leaders, wickets_leaders=wickets_leaders)

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

# -----------------------
# FANTASY STANDALONE ROUTES
# -----------------------

@app.route('/fantasy')
def fantasy():
    players = get_fantasy_leaderboard()
    # we reuse the premium animated leaderboard design for fantasy!
    return render_template('fantasy.html', players=players)

@app.route('/fantasy/matches/new', methods=['GET', 'POST'])
def add_fantasy_match():
    all_players = get_players()
    if request.method == 'POST':
        match_number = int(request.form.get('match_number', 1))
        player_scores = []
        for p in all_players:
            score_str = request.form.get(f"score_{p['id']}")
            fp_str = request.form.get(f"fantasy_points_{p['id']}")
            if score_str and score_str.strip() and fp_str and fp_str.strip():
                player_scores.append({
                    "player_id": p['id'],
                    "score": float(score_str),
                    "fantasy_points": float(fp_str)
                })
        
        if player_scores:
            try:
                create_premium_match(match_number, player_scores)
                flash(f"Fantasy Match #{match_number} securely locked and rankings evaluated!", "success")
            except Exception as e:
                flash(f"Error processing match ranking logic: {str(e)}", "error")
        else:
            flash("No scores entered! Match was empty and ignored.", "error")
            
        return redirect(url_for('fantasy_history'))
        
    return render_template('fantasy_match_form.html', players=all_players)

@app.route('/fantasy/matches')
def fantasy_history():
    matches = get_match_history()
    is_admin = 'admin_token' in session
    return render_template('fantasy_history.html', matches=matches, is_admin=is_admin)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
