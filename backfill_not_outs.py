from app import app
from models import supabase, get_players, recalculate_player_stats

def update_historic_not_outs():
    with app.app_context():
        print("Finding 'Not Out' players from historic live matches...")
        
        # 1. Get all live match players who finished with status 'batting'
        # To be safe, they must have either faced balls or scored runs to be considered a true "innings"
        res = supabase.table('live_match_players').select('*').eq('status', 'batting').execute()
        lmp_records = res.data
        
        updated_count = 0
        
        for lmp in lmp_records:
            match_log_id = lmp.get('match_log_id')
            balls = lmp.get('balls_faced', 0)
            runs = lmp.get('runs_scored', 0)
            is_striker = lmp.get('is_striker', False)
            is_non_striker = lmp.get('is_non_striker', False)
            
            # If they were truly batting at the crease
            if match_log_id and (balls > 0 or runs > 0 or is_striker or is_non_striker):
                # Update their match_log to indicate not_out
                supabase.table('match_logs').update({'not_out': True}).eq('id', match_log_id).execute()
                updated_count += 1
                print(f"Updated match log {match_log_id} to Not Out.")
        
        print(f"Successfully updated {updated_count} historic match logs to be Not Out.")
        
        print("Recalculating all player stats globally to reflect these changes...")
        players = get_players()
        for p in players:
            try:
                recalculate_player_stats(p['id'])
            except Exception as e:
                print(f"Error recalculating {p['name']}: {e}")
                
        print("Done!")

if __name__ == '__main__':
    update_historic_not_outs()
