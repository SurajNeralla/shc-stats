import os
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

supabase: Client = None

if url and key:
    supabase = create_client(url, key)

def get_players():
    return supabase.table("players").select("*, player_stats(*)").execute().data

def get_player(player_id):
    return supabase.table("players").select("*, player_stats(*)").eq("id", player_id).execute().data[0]

def create_player(data):
    if "total_score" not in data:
        data["total_score"] = 0
    return supabase.table("players").insert(data).execute()

def update_player(player_id, data):
    return supabase.table("players").update(data).eq("id", player_id).execute()

def delete_player(player_id):
    return supabase.table("players").delete().eq("id", player_id).execute()

def get_player_by_email(email):
    res = supabase.table("players").select("*").eq("email", email).execute()
    if res.data:
        return res.data[0]
    return None

def create_player_stats(data):
    return supabase.table("player_stats").insert(data).execute()

def update_player_stats(player_id, data):
    return supabase.table("player_stats").update(data).eq("player_id", player_id).execute()

def get_match_logs(player_id):
    res = supabase.table("match_logs").select("*").eq("player_id", player_id).order("match_date", desc=True).execute()
    return res.data

def recalculate_player_stats(player_id):
    logs = get_match_logs(player_id)
    matches = len(logs)
    runs = 0
    balls_faced = 0
    fours = 0
    sixes = 0
    fifties = 0
    thirties = 0
    hundreds = 0
    highest_score = 0
    
    innings_batted = 0
    not_outs = 0
    
    overs_bowled = 0.0
    maidens = 0
    runs_conceded = 0
    wickets = 0
    three_wkt_hauls = 0
    five_for_count = 0
    no_balls = 0
    wides = 0
    catches = 0
    stumpings = 0

    for l in logs:
        score = l.get('runs', 0)
        runs += score
        balls_f = l.get('balls_faced', 0)
        balls_faced += balls_f
        fours += l.get('fours', 0)
        sixes += l.get('sixes', 0)
        
        is_not_out = l.get('not_out', False)
        if balls_f > 0 or score > 0 or is_not_out:
            innings_batted += 1
            if is_not_out:
                not_outs += 1
        
        if score > highest_score:
            highest_score = score
        if score >= 100:
            hundreds += 1
        if score >= 50:
            fifties += 1
        if score >= 30:
            thirties += 1
            
        overs_b = l.get('overs_bowled', 0)
        overs_bowled += overs_b
        maidens += l.get('maidens', 0)
        runs_conceded += l.get('runs_conceded', 0)
        
        w = l.get('wickets', 0)
        wickets += w
        if w >= 5:
            five_for_count += 1
        if w >= 3:
            three_wkt_hauls += 1
            
        no_balls += l.get('no_balls', 0)
        wides += l.get('wides', 0)
        catches += l.get('catches', 0)
        stumpings += l.get('stumpings', 0)

    from math import floor
    total_balls = 0
    for l in logs:
        ob = l.get('overs_bowled', 0)
        full_o = floor(ob)
        rem_b = round((ob - full_o) * 10)
        total_balls += (full_o * 6) + rem_b
        
    final_full_overs = total_balls // 6
    final_rem_balls = total_balls % 6
    calculated_overs = final_full_overs + (final_rem_balls / 10.0)

    dismissals = innings_batted - not_outs

    stats_data = {
        "matches": matches,
        "innings_batted": innings_batted,
        "not_outs": not_outs,
        "dismissals": dismissals,
        "runs": runs,
        "balls_faced": balls_faced,
        "fours": fours,
        "sixes": sixes,
        "fifties": fifties,
        "thirties": thirties,
        "hundreds": hundreds,
        "highest_score": highest_score,
        "overs_bowled": calculated_overs,
        "maidens": maidens,
        "runs_conceded": runs_conceded,
        "wickets": wickets,
        "three_wkt_hauls": three_wkt_hauls,
        "five_fives": five_for_count,
        "no_balls": no_balls,
        "wides": wides,
        "catches": catches,
        "stumpings": stumpings
    }
    update_player_stats(player_id, stats_data)

def add_match_log(player_id, log_data):
    log_data['player_id'] = player_id
    supabase.table("match_logs").insert(log_data).execute()
    recalculate_player_stats(player_id)

def delete_match_log(log_id, player_id):
    supabase.table("match_logs").delete().eq("id", log_id).execute()
    recalculate_player_stats(player_id)

def get_leaderboard_runs():
    res = supabase.table("player_stats").select("*, players(*)").order("runs", desc=True).limit(10).execute()
    return res.data

def get_leaderboard_wickets():
    res = supabase.table("player_stats").select("*, players(*)").order("wickets", desc=True).limit(10).execute()
    return res.data

# --- LIVE MATCH MODULE ---

def create_live_match(data):
    return supabase.table("live_matches").insert(data).execute()

def get_live_match(match_id):
    res = supabase.table("live_matches").select("*").eq("id", match_id).execute()
    return res.data[0] if res.data else None

def update_live_match(match_id, data):
    return supabase.table("live_matches").update(data).eq("id", match_id).execute()

def create_live_match_players(data_list):
    return supabase.table("live_match_players").insert(data_list).execute()

def get_live_match_players(match_id):
    return supabase.table("live_match_players").select("*, players(*)").eq("live_match_id", match_id).execute().data

def update_live_match_player(lmp_id, data):
    return supabase.table("live_match_players").update(data).eq("id", lmp_id).execute()

def log_live_ball(match_id, ball_data):
    # Log the exact ball event
    ball_data["live_match_id"] = match_id
    supabase.table("live_match_balls").insert(ball_data).execute()
    
    # After a ball is logged, the caller handles updating live_match_players and live_matches
    # Then we run live sync by updating the global match_logs and recalculating player stats
    
def sync_player_career_stats(lmp_record):
    """
    Takes a single live_match_player record, updates (or creates) its 
    corresponding match_logs entry, and triggers global recalculate.
    """
    if not lmp_record.get('match_log_id'):
        # Create initial dummy match log
        log_data = {
            'player_id': lmp_record['player_id'],
            'opponent': 'Live Match',
            'runs': 0, 'balls_faced': 0, 'fours': 0, 'sixes': 0, 'not_out': False,
            'overs_bowled': 0, 'maidens': 0, 'runs_conceded': 0, 'wickets': 0, 'no_balls': 0, 'wides': 0
        }
        res = supabase.table("match_logs").insert(log_data).execute()
        if res.data:
            match_log_id = res.data[0]['id']
            update_live_match_player(lmp_record['id'], {'match_log_id': match_log_id})
            lmp_record['match_log_id'] = match_log_id
            
    # Calculate overs properly
    balls = lmp_record.get('balls_bowled', 0)
    overs_b = (balls // 6) + ((balls % 6) / 10.0)

    is_not_out = False
    status = lmp_record.get('status')
    if status == 'batting' and (lmp_record.get('balls_faced', 0) > 0 or lmp_record.get('runs_scored', 0) > 0 or lmp_record.get('is_striker') or lmp_record.get('is_non_striker')):
        is_not_out = True

    sync_data = {
        'not_out': is_not_out,
        'runs': lmp_record.get('runs_scored', 0),
        'balls_faced': lmp_record.get('balls_faced', 0),
        'fours': lmp_record.get('fours', 0),
        'sixes': lmp_record.get('sixes', 0),
        'overs_bowled': overs_b,
        'maidens': lmp_record.get('maidens', 0),
        'runs_conceded': lmp_record.get('runs_conceded', 0),
        'wickets': lmp_record.get('wickets_taken', 0),
        # Wides and No-balls per bowler aren't strictly tracked in the live_match_players table yet, 
        # but could be added if needed, right now we just push standard stats.
    }
    supabase.table("match_logs").update(sync_data).eq("id", lmp_record['match_log_id']).execute()
    # defer recalculate_player_stats to end of match to save time

def get_all_live_matches():
    return supabase.table("live_matches").select("*").in_("status", ["setup", "innings_1", "innings_2"]).order("created_at", desc=True).execute().data

def get_completed_matches():
    return supabase.table("live_matches").select("*").eq("status", "completed").order("created_at", desc=True).execute().data
    
def delete_live_match(match_id):
    players = get_live_match_players(match_id)
    for p in players:
        if p.get('match_log_id'):
            supabase.table("match_logs").delete().eq("id", p['match_log_id']).execute()
            recalculate_player_stats(p['player_id'])
    return supabase.table("live_matches").delete().eq("id", match_id).execute()

def undo_last_ball(match_id):
    res = supabase.table("live_match_balls").select("*").eq("live_match_id", match_id).order("created_at", desc=True).limit(1).execute()
    if not res.data: return False
    
    ball = res.data[0]
    supabase.table("live_match_balls").delete().eq("id", ball['id']).execute()
    
    match = get_live_match(match_id)
    players = get_live_match_players(match_id)
    
    striker_lmp = next((p for p in players if p['player_id'] == ball['striker_id']), None)
    bowler_lmp = next((p for p in players if p['player_id'] == ball['bowler_id']), None)
    
    if not striker_lmp or not bowler_lmp: return False
        
    team_prefix = striker_lmp['team']
    
    # Restore Match
    new_team_score = match.get(team_prefix + '_score', 0) - ball.get('runs', 0) - ball.get('extras', 0)
    is_legal = not ball.get('extra_type')
    new_team_balls = match.get(team_prefix + '_balls', 0) - (1 if is_legal else 0)
    new_team_wickets = match.get(team_prefix + '_wickets', 0) - (1 if ball.get('is_wicket') else 0)
    
    update_live_match(match_id, {
        team_prefix + '_score': max(0, new_team_score),
        team_prefix + '_balls': max(0, new_team_balls),
        team_prefix + '_wickets': max(0, new_team_wickets)
    })
    
    # Restore Striker
    s_runs = striker_lmp['runs_scored'] - ball.get('runs', 0)
    s_balls = striker_lmp['balls_faced'] - (0 if ball.get('extra_type') == 'wide' else 1)
    if ball.get('extra_type') == 'no-ball' and ball.get('runs', 0) == 0: s_balls += 1 # We didn't add a ball if it was a no-ball with 0 runs
    s_fours = striker_lmp['fours'] - (1 if ball.get('runs') == 4 else 0)
    s_sixes = striker_lmp['sixes'] - (1 if ball.get('runs') == 6 else 0)
    
    update_live_match_player(striker_lmp['id'], {
        'runs_scored': max(0, s_runs),
        'balls_faced': max(0, s_balls),
        'fours': max(0, s_fours),
        'sixes': max(0, s_sixes),
        'status': 'batting' if ball.get('is_wicket') else striker_lmp['status'],
        'is_striker': True,
        'is_non_striker': False
    })
    
    # Restore Bowler
    b_runs = bowler_lmp['runs_conceded'] - ball.get('runs', 0) - ball.get('extras', 0)
    b_balls = bowler_lmp['balls_bowled'] - (1 if is_legal else 0)
    b_wickets = bowler_lmp['wickets_taken'] - (1 if ball.get('is_wicket') else 0)
    update_live_match_player(bowler_lmp['id'], {
        'runs_conceded': max(0, b_runs),
        'balls_bowled': max(0, b_balls),
        'wickets_taken': max(0, b_wickets),
        'is_current_bowler': True
    })
    
    # Restore non-striker
    non_striker_id = ball.get('non_striker_id')
    if non_striker_id:
        ns_lmp = next((p for p in players if p['player_id'] == non_striker_id), None)
        if ns_lmp:
            update_live_match_player(ns_lmp['id'], {'is_striker': False, 'is_non_striker': True})
            
    # Re-sync
    striker_lmp.update({'runs_scored': max(0, s_runs), 'balls_faced': max(0, s_balls), 'fours': max(0, s_fours), 'sixes': max(0, s_sixes)})
    sync_player_career_stats(striker_lmp)
    # Recalculate manually for undo to keep it consistent if needed, but we deferred it above. 
    # For undo, we can do it because it's rare.
    recalculate_player_stats(striker_lmp['player_id'])
    
    bowler_lmp.update({'runs_conceded': max(0, b_runs), 'balls_bowled': max(0, b_balls), 'wickets_taken': max(0, b_wickets)})
    sync_player_career_stats(bowler_lmp)
    recalculate_player_stats(bowler_lmp['player_id'])
    
    return True

def get_live_match_ball_logs(match_id):
    res = supabase.table("live_match_balls").select("*").eq("live_match_id", match_id).order("created_at", desc=False).execute()
    return res.data
