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
    
    ones = 0
    twos = 0
    
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
        ones += l.get('ones', 0)
        twos += l.get('twos', 0)
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
        "ones": ones,
        "twos": twos,
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

def get_leaderboard_fours():
    res = supabase.table("player_stats").select("*, players(*)").order("fours", desc=True).limit(10).execute()
    return res.data

def get_leaderboard_sixes():
    res = supabase.table("player_stats").select("*, players(*)").order("sixes", desc=True).limit(10).execute()
    return res.data

def get_leaderboard_ones():
    res = supabase.table("player_stats").select("*, players(*)").order("ones", desc=True).limit(10).execute()
    return res.data

def get_leaderboard_twos():
    res = supabase.table("player_stats").select("*, players(*)").order("twos", desc=True).limit(10).execute()
    return res.data


