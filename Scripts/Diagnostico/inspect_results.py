
import os, json
pasta = r'C:\Users\rodri\OneDrive\Documentos\iRacing\aiseasons'
if os.path.isdir(pasta):
    for f in os.listdir(pasta):
        if not f.endswith('.json'): continue
        path = os.path.join(pasta, f)
        with open(path, 'r', encoding='utf-8') as file:
            try: data = json.load(file)
            except: continue
            events = data.get('events', [])
            for ev in events:
                if 'results' in ev and ev['results']:
                    for sess in ev['results'].get('session_results', []):
                        if sess.get('simsession_type_name') == 'Race':
                            res = sess['results']
                            print(json.dumps(res[0], indent=2))
                            import sys; sys.exit(0)

