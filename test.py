import re
from app import app
with app.app_context():
    from models import supabase
    match = supabase.table('live_matches').select('id').order('created_at', desc=True).limit(1).execute().data[0]
    match_id = match['id']
    
    with app.test_client() as client:
        res = client.get('/live-match/' + match_id + '/scorecard')
        html = res.data.decode('utf-8')
        matches = re.finditer(r'<span id=\"(?P<id>striker-name|nonstriker-name|bowler-name)\"[^>]*>(?P<val>.*?)</span>', html)
        for m in matches:
            print(m.group('id') + ' = ' + m.group('val'))
