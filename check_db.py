from app import supabase
matches = supabase.table('live_matches').select('*').in_('status', ['setup', 'innings_1', 'innings_2']).order('created_at', desc=True).limit(1).execute().data
if matches:
    match = matches[0]
    print('Match ID:', match['id'])
    print('Status:', match['status'])
    print('Team A score:', match.get('team_a_score'), '/', match.get('team_a_wickets'), 'Balls:', match.get('team_a_balls'))
    print('Team B score:', match.get('team_b_score'), '/', match.get('team_b_wickets'), 'Balls:', match.get('team_b_balls'))
    players = supabase.table('live_match_players').select('*, players(name)').eq('live_match_id', match['id']).execute().data
    for p in players:
        print(f"{p['players']['name']}: Striker:{p['is_striker']} Non:{p['is_non_striker']} Bowler:{p['is_current_bowler']} Runs:{p['runs_scored']} Balls:{p['balls_faced']}")
