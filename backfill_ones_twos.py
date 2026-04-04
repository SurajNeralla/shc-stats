import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def backfill():
    print("Fetching all live match balls...")
    balls = supabase.table("live_match_balls").select("*").execute().data
    print(f"Found {len(balls)} balls.")

    # Dictionary to track updates: match_log_id -> {'ones': count, 'twos': count}
    log_updates = {}

    # Map (live_match_id, player_id) -> match_log_id
    print("Fetching live match players to mapping...")
    lmps = supabase.table("live_match_players").select("live_match_id, player_id, match_log_id").execute().data
    player_log_map = {(p['live_match_id'], p['player_id']): p['match_log_id'] for p in lmps if p.get('match_log_id')}

    for ball in balls:
        runs = ball.get('runs', 0)
        if runs in [1, 2]:
            mid = ball['live_match_id']
            pid = ball['striker_id']
            log_id = player_log_map.get((mid, pid))
            
            if log_id:
                if log_id not in log_updates:
                    log_updates[log_id] = {'ones': 0, 'twos': 0}
                
                if runs == 1:
                    log_updates[log_id]['ones'] += 1
                elif runs == 2:
                    log_updates[log_id]['twos'] += 1

    print(f"Found {len(log_updates)} match logs to update.")

    affected_players = set()

    for log_id, updates in log_updates.items():
        print(f"Updating match log {log_id}: {updates}")
        res = supabase.table("match_logs").update(updates).eq("id", log_id).execute()
        if res.data:
            affected_players.add(res.data[0]['player_id'])

    print(f"Recalculating stats for {len(affected_players)} players...")
    # Import the function from models (this script needs to be run in an environment where models is importable)
    from models import recalculate_player_stats
    for pid in affected_players:
        print(f"Recalculating for player {pid}...")
        recalculate_player_stats(pid)

    print("Backfill complete!")

if __name__ == "__main__":
    backfill()
