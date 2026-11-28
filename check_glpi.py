"""Diagnostic de connexion GLPI (bibliothèque standard uniquement).
Usage:  python check_glpi.py
Lit .env, puis teste pas à pas: URL -> DNS -> initSession -> profil -> entités -> tickets."""
import json, os, socket, ssl, sys, urllib.error, urllib.parse, urllib.request
from app import load_dotenv
load_dotenv()

def step(ok, msg, hint=''):
    print(('  [OK]   ' if ok else '  [ECHEC]'), msg)
    if not ok and hint: print('         ->', hint)
    return ok

base = os.getenv('GLPI_BASE_URL', '').rstrip('/'); app_tok = os.getenv('GLPI_APP_TOKEN', ''); usr_tok = os.getenv('GLPI_USER_TOKEN', '')
print('Test de connexion GLPI\n')
if not step(bool(base and app_tok and usr_tok), 'Variables GLPI_BASE_URL / GLPI_APP_TOKEN / GLPI_USER_TOKEN présentes', 'Remplissez-les dans .env'): sys.exit(1)
u = urllib.parse.urlparse(base)
if not step(u.scheme in ('http', 'https') and bool(u.hostname), f'URL valide: {base}', 'Exemple: http://192.168.1.20/glpi  (sans /apirest.php à la fin)'): sys.exit(1)
if u.scheme == 'http' and u.hostname not in ('localhost', '127.0.0.1') and os.getenv('GLPI_ALLOW_HTTP', '').lower() != 'true':
    print('  [INFO] http:// sur un serveur non local: ajoutez GLPI_ALLOW_HTTP=true dans .env (réseau interne/test seulement).')
try:
    ip = socket.gethostbyname(u.hostname); step(True, f'DNS: {u.hostname} -> {ip}')
except OSError as e:
    step(False, f'DNS: impossible de résoudre {u.hostname} ({e})', "Ce nom n'existe pas sur cette machine. Utilisez l'adresse IP du serveur GLPI, ou ajoutez le nom au fichier hosts."); sys.exit(1)
ctx = ssl._create_unverified_context() if u.scheme == 'https' and os.getenv('GLPI_VERIFY_TLS', 'true').lower() == 'false' else None
root = base + '/apirest.php'

def call(path, headers):
    req = urllib.request.Request(root + path, headers={**headers, 'Accept': 'application/json'})
    with (urllib.request.urlopen(req, timeout=8, context=ctx) if ctx else urllib.request.urlopen(req, timeout=8)) as r: return json.loads(r.read() or b'null')

def fail(e):
    if isinstance(e, urllib.error.HTTPError):
        body = e.read().decode('utf-8', 'replace')[:300]
        hints = {'ERROR_WRONG_APP_TOKEN_PARAMETER': "App-Token incorrect: GLPI > Configuration > Générale > API > Clients de l'API > votre client",
                 'ERROR_GLPI_LOGIN_USER_TOKEN': "User-Token incorrect: GLPI > Préférences de l'utilisateur > Clé d'accès distant (regénérez-la)",
                 'ERROR_API_DISABLED': "API REST désactivée: Configuration > Générale > API > activer l'API REST",
                 'ERROR_NOT_ALLOWED_IP': "IP non autorisée: ajoutez l'IP de ce PC dans le client d'API (ou laissez 0.0.0.0/0 en test)"}
        hint = next((v for k, v in hints.items() if k in body), 'Voir le message GLPI ci-dessus')
        return f'HTTP {e.code}: {body}', hint
    return f'{type(e).__name__}: {getattr(e, "reason", e)}', "Serveur GLPI injoignable (pare-feu, mauvais port, TLS auto-signé -> GLPI_VERIFY_TLS=false)"

try:
    tok = call('/initSession', {'App-Token': app_tok, 'Authorization': 'user_token ' + usr_tok})['session_token']; step(True, 'initSession: authentification acceptée')
except Exception as e:
    m, h = fail(e); step(False, 'initSession ' + m, h); sys.exit(1)
H = {'App-Token': app_tok, 'Session-Token': tok}
try:
    s = call('/getFullSession', H)['session']; step(True, f"Session: profil « {s.get('glpiactiveprofile', {}).get('name', '?')} », utilisateur id {s.get('glpiID')}")
    print(f"         (mettez glpi_user_id = {s.get('glpiID')} pour le compte local lié à cet utilisateur GLPI)")
except Exception as e: m, h = fail(e); step(False, 'getFullSession ' + m, h)
try:
    ents = call('/Entity?range=0-199', H); step(True, f'Entités visibles: {len(ents)}')
    for x in ents: print(f"         id={x['id']:<4} {x.get('completename') or x.get('name')}")
except Exception as e: m, h = fail(e); step(False, 'Entités ' + m, h)
try:
    t = call('/search/Ticket?range=0-4', H); step(True, f"Tickets: {t.get('totalcount', 0)} trouvé(s) pour ce profil")
except Exception as e: m, h = fail(e); step(False, 'Recherche tickets ' + m, h)
try: call('/killSession', H)
except Exception: pass
print('\nTerminé.')
