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
    if "total_fantasy_points" not in data:
        data["total_fantasy_points"] = 0
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
    hundreds = 0
    highest_score = 0
    
    overs_bowled = 0.0
    maidens = 0
    runs_conceded = 0
    wickets = 0
    no_balls = 0
    wides = 0
    catches = 0
    stumpings = 0

    for l in logs:
        score = l.get('runs', 0)
        runs += score
        balls_faced += l.get('balls_faced', 0)
        fours += l.get('fours', 0)
        sixes += l.get('sixes', 0)
        
        if score > highest_score:
            highest_score = score
        if score >= 100:
            hundreds += 1
        elif score >= 50:
            fifties += 1
            
        overs_b = l.get('overs_bowled', 0)
        overs_bowled += overs_b
        maidens += l.get('maidens', 0)
        runs_conceded += l.get('runs_conceded', 0)
        wickets += l.get('wickets', 0)
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

    stats_data = {
        "matches": matches,
        "runs": runs,
        "balls_faced": balls_faced,
        "fours": fours,
        "sixes": sixes,
        "fifties": fifties,
        "hundreds": hundreds,
        "highest_score": highest_score,
        "overs_bowled": calculated_overs,
        "maidens": maidens,
        "runs_conceded": runs_conceded,
        "wickets": wickets,
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

# --- FANTASY RANK/POINTS ENGINE ---
def create_premium_match(match_number, player_scores_list):
    player_scores_list.sort(key=lambda x: (x['score'], x['fantasy_points']), reverse=True)
    
    for i in range(len(player_scores_list)):
        if i > 0:
            prev = player_scores_list[i-1]
            curr = player_scores_list[i]
            if curr['score'] == prev['score'] and curr['fantasy_points'] == prev['fantasy_points']:
                curr['rank'] = prev['rank']
            else:
                curr['rank'] = i + 1
        else:
            player_scores_list[i]['rank'] = 1
            
    match_resp = supabase.table("matches").insert({
        "match_number": match_number,
        "locked": True
    }).execute()
    
    match_id = match_resp.data[0]['id']
    
    entries_to_insert = []
    for p in player_scores_list:
        entries_to_insert.append({
            "match_id": match_id,
            "player_id": p['player_id'],
            "score": p['score'],
            "fantasy_points": p['fantasy_points'],
            "rank": p['rank']
        })
    supabase.table("entries").insert(entries_to_insert).execute()
    
    players_resp = supabase.table("players").select("id, total_score, total_fantasy_points").execute().data
    player_data = {p['id']: p for p in players_resp}
    
    for p in player_scores_list:
        pt = player_data.get(p['player_id'], {})
        new_score = (pt.get('total_score') or 0) + p['score']
        new_fp = (pt.get('total_fantasy_points') or 0) + p['fantasy_points']
        supabase.table("players").update({
            "total_score": new_score,
            "total_fantasy_points": new_fp
        }).eq("id", p['player_id']).execute()

def get_match_history():
    data = supabase.table("matches").select("id, match_number, created_at, locked, entries(id, score, fantasy_points, rank, players(id, name, image_url))").order("match_number", desc=True).execute().data
    for m in data:
        m['entries'].sort(key=lambda x: x['rank'])
    return data

def get_fantasy_leaderboard():
    return supabase.table("players").select("*").order("total_score", desc=True).order("total_fantasy_points", desc=True).execute().data

def get_fantasy_match(match_id):
    """Fetch a single match with all its entries and player details."""
    res = supabase.table("matches").select(
        "id, match_number, entries(id, score, fantasy_points, rank, player_id, players(id, name, image_url, total_score, total_fantasy_points))"
    ).eq("id", match_id).execute()
    if res.data:
        match = res.data[0]
        match['entries'].sort(key=lambda x: x['rank'])
        return match
    return None

def recalculate_all_player_totals():
    """Rebuild total_score and total_fantasy_points for every player from scratch."""
    all_entries = supabase.table("entries").select("player_id, score, fantasy_points").execute().data
    totals = {}
    for e in all_entries:
        pid = e['player_id']
        if pid not in totals:
            totals[pid] = {'total_score': 0.0, 'total_fantasy_points': 0.0}
        totals[pid]['total_score'] += float(e.get('score') or 0)
        totals[pid]['total_fantasy_points'] += float(e.get('fantasy_points') or 0)

    # Zero-out players with no entries at all
    all_players = supabase.table("players").select("id").execute().data
    for p in all_players:
        pid = p['id']
        if pid not in totals:
            totals[pid] = {'total_score': 0.0, 'total_fantasy_points': 0.0}

    for pid, data in totals.items():
        supabase.table("players").update(data).eq("id", pid).execute()

def update_fantasy_match(match_id, player_scores_list):
    """Update entries in a match, re-rank, then recalculate all player totals from scratch."""
    # Recalculate ranks based on new scores
    player_scores_list.sort(key=lambda x: (x['score'], x['fantasy_points']), reverse=True)
    for i in range(len(player_scores_list)):
        if i > 0:
            prev = player_scores_list[i - 1]
            curr = player_scores_list[i]
            if curr['score'] == prev['score'] and curr['fantasy_points'] == prev['fantasy_points']:
                curr['rank'] = prev['rank']
            else:
                curr['rank'] = i + 1
        else:
            player_scores_list[i]['rank'] = 1

    # Push updated entries to DB
    for p in player_scores_list:
        supabase.table("entries").update({
            "score": p['score'],
            "fantasy_points": p['fantasy_points'],
            "rank": p['rank']
        }).eq("id", p['entry_id']).execute()

    # Rebuild all player totals cleanly from scratch
    recalculate_all_player_totals()
