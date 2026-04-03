from app import supabase

with open('db_out.txt', 'w') as f:
    matches = supabase.table('live_matches').select('*').in_('status', ['setup', 'innings_1', 'innings_2']).order('created_at', desc=True).limit(1).execute().data
    if matches:
        match = matches[0]
        f.write(f"Match ID: {match['id']}\n")
        f.write(f"Status: {match['status']}\n")
        f.write(f"Team A score: {match.get('team_a_score')} / {match.get('team_a_wickets')} Balls: {match.get('team_a_balls')}\n")
        f.write(f"Team B score: {match.get('team_b_score')} / {match.get('team_b_wickets')} Balls: {match.get('team_b_balls')}\n")
        players = supabase.table('live_match_players').select('*, players(name)').eq('live_match_id', match['id']).execute().data
        for p in players:
            f.write(f"{p['players']['name']}: Striker:{p['is_striker']} Non:{p['is_non_striker']} Bowler:{p['is_current_bowler']} Runs:{p['runs_scored']} Balls:{p['balls_faced']}\n")
