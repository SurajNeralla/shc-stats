from app import app
from models import get_leaderboard_runs

with app.app_context():
    for l in get_leaderboard_runs():
        print(f"Name: {l['players']['name']}, Innings: {l['innings_batted']}, NO: {l['not_outs']}, Dismissals: {l['dismissals']}, Runs: {l['runs']}, Avg: {l['runs'] / l['dismissals'] if l['dismissals'] > 0 else l['runs']}")
