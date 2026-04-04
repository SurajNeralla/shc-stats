from app import app
from models import get_players, recalculate_player_stats

def main():
    with app.app_context():
        players = get_players()
        print(f"Recalculating stats for {len(players)} players...")
        for p in players:
            player_id = p['id']
            try:
                recalculate_player_stats(player_id)
                print(f"Successfully recalculated: {p['name']}")
            except Exception as e:
                print(f"Error recalculating {p['name']}: {e}")
        print("Done!")

if __name__ == '__main__':
    main()
