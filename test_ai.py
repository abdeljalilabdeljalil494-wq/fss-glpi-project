"""Teste directement le fournisseur IA avec les valeurs de .env et affiche la VRAIE raison de l'échec.
Usage:  python test_ai.py"""
import json, os, urllib.error, urllib.request
from app import load_dotenv
load_dotenv()
base = os.getenv('AI_BASE_URL', '').rstrip('/'); key = os.getenv('AI_API_KEY', ''); model = os.getenv('AI_MODEL', '')
print('AI_BASE_URL =', base or '(vide)'); print('AI_MODEL    =', model or '(vide)'); print('AI_API_KEY  =', (key[:4] + '... (' + str(len(key)) + ' caractères)') if key else '(vide)')
if not (base and key and model): raise SystemExit('\n[ECHEC] Une des 3 variables AI_* est vide dans .env')
if 'example.com' in base: raise SystemExit('\n[ECHEC] AI_BASE_URL contient encore api.example.com : mettez https://api.groq.com/openai/v1')
req = urllib.request.Request(base + '/chat/completions', data=json.dumps({'model': model, 'messages': [{'role': 'user', 'content': 'Dis bonjour en une phrase.'}], 'max_tokens': 40}).encode(),
    headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json', 'Accept': 'application/json', 'User-Agent': 'fss-glpi-assistant/1.0'}, method='POST')
try:
    with urllib.request.urlopen(req, timeout=25) as r: out = json.loads(r.read())
    print('\n[OK] Réponse du modèle :', out['choices'][0]['message']['content'])
except urllib.error.HTTPError as e:
    hint = {401: 'Clé API invalide ou révoquée: créez-en une nouvelle sur console.groq.com',
            403: 'Accès refusé par le fournisseur (clé, région ou règles du fournisseur)',
            404: "URL ou nom du modèle introuvable: vérifiez AI_BASE_URL et AI_MODEL",
            429: 'Limite atteinte: attendez une minute'}.get(e.code, 'Erreur du fournisseur')
    print(f'\n[ECHEC] HTTP {e.code}: {hint}\nMessage du fournisseur: {e.read().decode("utf-8", "replace")[:400]}')
except Exception as e:
    print(f'\n[ECHEC] {type(e).__name__}: {getattr(e, "reason", e)}\n-> Pas d\'accès au fournisseur: internet, DNS, proxy ou pare-feu.')
