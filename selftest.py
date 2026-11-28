"""Auto-test de toute l'application (GLPI, IA, entités, tickets, stock, agents, isolation, ronde).
1) Lancez l'application dans une autre fenêtre:   python app.py
2) Ici:                                          python selftest.py          (ou: python selftest.py --yes  pour tout accepter)
Les étapes qui ÉCRIVENT dans GLPI demandent confirmation. Le mot de passe n'est envoyé qu'à l'application locale."""
import getpass, json, os, secrets, sys, time, urllib.error, urllib.request
BASE = next((a for a in sys.argv[1:] if a.startswith('http')), 'http://127.0.0.1:8000').rstrip('/')
YES = '--yes' in sys.argv
passed = failed = 0
tid_test = None
test_user_id = None

class Client:
    def __init__(self): self.cookie = ''
    def raw(self, path):
        req = urllib.request.Request(BASE + path, headers={'Cookie': self.cookie})
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return r.status, r.read(), r.headers.get('Content-Type', '')
        except urllib.error.HTTPError as e: return e.code, b'', ''
        except Exception as e: return 0, str(e).encode(), ''
    def call(self, method, path, body=None, timeout=120):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(BASE + path, data=data, method=method, headers={'Content-Type': 'application/json', 'Cookie': self.cookie})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                for h in r.headers.get_all('Set-Cookie') or []:
                    if not h.split(';')[0].endswith('='): self.cookie = h.split(';')[0]
                return r.status, json.loads(r.read() or b'null')
        except urllib.error.HTTPError as e:
            try: return e.code, json.loads(e.read() or b'null')
            except Exception: return e.code, {'error': 'réponse non JSON'}
        except Exception as e:
            return 0, {'error': f'{type(e).__name__}: {getattr(e, "reason", e)}'}

def ok(cond, name, detail=''):
    global passed, failed
    if cond: passed += 1
    else: failed += 1
    print(('  [OK]     ' if cond else '  [ECHEC]  ') + name + ((' -> ' + str(detail)) if detail and not cond else ''))
    return cond
def info(msg): print('  [INFO]   ' + msg)
def title(t): print('\n== ' + t + ' ==')
def err(r): return (r[1] or {}).get('error', r[1]) if isinstance(r[1], dict) else r[1]
def ask(q): return YES or input(f'\n{q} (o/N) ').strip().lower() in ('o', 'y', 'oui', 'yes')

print('Auto-test de l\'application sur', BASE)
a = Client(); s, h = a.call('GET', '/api/health')
if s != 200: raise SystemExit(f'\n[ECHEC] Application injoignable ({err((s, h))}). Lancez d\'abord: python app.py')
user = os.getenv('SELFTEST_USER') or input("Compte administrateur [admin]: ").strip() or 'admin'
pw = os.getenv('SELFTEST_PASSWORD') or getpass.getpass('Mot de passe: ')
r = a.call('POST', '/api/auth/login', {'username': user, 'password': pw})
if r[0] != 200: raise SystemExit(f'\n[ECHEC] Connexion refusée: {err(r)}')
me = r[1]['user']; ok(me['role'] == 'admin', 'Connecté en administrateur', 'ce test doit tourner avec un compte admin')

title('1. Configuration et connexions')
ok(h.get('glpi') == 'configured', 'GLPI configuré dans .env', 'remplissez GLPI_* dans .env'); ok(h.get('ai') == 'configured', 'IA configurée dans .env', 'remplissez AI_* dans .env')
r = a.call('GET', '/api/glpi/health'); ok(r[0] == 200 and r[1].get('status') == 'connected', 'Connexion réelle à GLPI', err(r))
users = (a.call('GET', '/api/admin/users')[1] or {}).get('users', []); mine = next((u for u in users if u['username'] == me['username']), {})
has_gid = bool(mine.get('glpi_user_id')); ok(has_gid, 'Votre compte est lié à un ID utilisateur GLPI', 'Administration > Comptes > Modifier > ID GLPI (ex. 2)')

title('2. Entités de stock (GLPI)')
r = a.call('GET', '/api/admin/entities'); ents = (r[1] or {}).get('entities', [])
ok(len(ents) == 7 and all(e['glpi_entity_id'] is not None for e in ents), '7 stocks liés à un ID GLPI', 'Administration > « Créer / synchroniser les 7 entités dans GLPI »')
r = a.call('POST', '/api/admin/entities/verify', {}); bad = [e['code'] for e in (r[1] or {}).get('entities', []) if e['glpi_entity_id'] is not None and e['verified'] != 1]
ok(r[0] == 200 and not bad, 'Les 7 entités existent réellement dans GLPI', f'{err(r) if r[0] != 200 else "introuvables: " + ", ".join(bad)} (relancez « Créer / synchroniser »)')

title('3. Tickets')
r = a.call('GET', '/api/ticket/options'); ok(r[0] == 200, 'Catégories de ticket (GLPI)', err(r)); info(f"{len((r[1] or {}).get('categories', []))} catégorie(s) visible(s) au helpdesk (0 = champ masqué dans le formulaire)")
r = a.call('GET', '/api/tickets'); ok(r[0] == 200, 'Lecture des tickets depuis GLPI', err(r))
if r[0] == 200: info(f"{len((r[1].get('data') or {}).get('data', [])) if isinstance(r[1], dict) and isinstance(r[1].get('data'), dict) else '?'} ticket(s) visibles")
if has_gid and ask('Créer un ticket de test dans GLPI ?'):
    r = a.call('POST', '/api/tickets', {'name': 'Auto-test FSS ' + time.strftime('%H:%M:%S'), 'content': 'Ticket créé par selftest.py, à supprimer.', 'type': 1, 'urgency': 4, 'place': 'selftest'})
    if ok(r[0] in (200, 201), 'Création d\'un ticket dans GLPI', err(r)):
        d = (r[1] or {}).get('data') or {}; tid = d.get('id') if isinstance(d, dict) else None
        if isinstance(tid, int):
            tid_test = tid
            for stt, lab in ((2, 'En cours'), (4, 'En attente (bloqué)'), (5, 'Résolu: crée une solution GLPI')):
                r = a.call('POST', '/api/admin/tickets/status', {'ticket_id': tid, 'status': stt, 'comment': 'selftest'})
                real = (a.call('GET', f'/api/tickets/{tid}')[1] or {}).get('data', {}).get('status')
                ok(r[0] == 200 and not (r[1] or {}).get('warning') and str(real) == str(stt), f'Changement d\'état du ticket #{tid} -> {lab}', err(r) if r[0] != 200 else ((r[1] or {}).get('warning') or f'GLPI affiche l\'état {real}'))
            h = (a.call('GET', f'/api/admin/tickets/history?ticket_id={tid}')[1] or {}).get('events', []); ok(len(h) >= 3, 'Historique des changements enregistré', f'{len(h)} événement(s)')
            info(f'Ticket de test #{tid} laissé à l\'état Résolu (GLPI ne permet pas de le supprimer via l\'API)')
        else: info("Id du ticket non reçu: test des états ignoré")

title('4. Stock (consommables GLPI)')
item = None
if ask('Créer un article de TEST dans STOCK-01 (écrit dans GLPI) ?'):
    name = 'ZZ-AutoTest-' + time.strftime('%H%M%S'); r = a.call('POST', '/api/stock/items', {'code': 'STOCK-01', 'name': name, 'quantity': 5, 'threshold': 6})
    items = (r[1] or {}).get('items', []); item = next((i for i in items if i['name'] == name), None)
    if ok(r[0] == 201 and item, 'Création article + 5 unités dans GLPI', err(r)):
        ok(item['quantity'] == 5, 'Quantité lue dans GLPI = 5', f"obtenu {item['quantity']}"); ok(item['low'], 'Alerte « sous le seuil » (5 <= 6)')
        r = a.call('POST', '/api/stock/entry', {'code': 'STOCK-01', 'item_id': item['id'], 'quantity': 3}); it = next((i for i in (r[1] or {}).get('items', []) if i['id'] == item['id']), {})
        ok(r[0] == 200 and it.get('quantity') == 8, 'Entrée +3 => 8', err(r) if r[0] != 200 else f"obtenu {it.get('quantity')}"); ok(it.get('low') is False, 'Alerte levée (8 > 6)')
        if has_gid:
            r = a.call('POST', '/api/stock/exit', {'code': 'STOCK-01', 'item_id': item['id'], 'quantity': 2}); it = next((i for i in (r[1] or {}).get('items', []) if i['id'] == item['id']), {})
            ok(r[0] == 200 and it.get('quantity') == 6, 'Sortie -2 => 6 (la partie la plus risquée avec GLPI)', err(r) if r[0] != 200 else f"obtenu {it.get('quantity')}")
            r = a.call('POST', '/api/stock/exit', {'code': 'STOCK-01', 'item_id': item['id'], 'quantity': 100}); ok(r[0] == 400, 'Sortie de 100 unités refusée (stock insuffisant)', f'statut {r[0]}')
        else: info('Sortie ignorée: lier votre compte à un ID GLPI')
        r = a.call('POST', '/api/stock/items/update', {'code': 'STOCK-01', 'item_id': item['id'], 'name': item['name'] + '-bis', 'threshold': 7}); it = next((i for i in (r[1] or {}).get('items', []) if i['id'] == item['id']), {})
        ok(r[0] == 200 and it.get('name') == item['name'] + '-bis' and it.get('threshold') == 7, 'Modification du nom et du seuil dans GLPI', err(r) if r[0] != 200 else it)
        if it: item['name'] = it['name']
else: info('Étape ignorée')

r = a.call('GET', '/api/stocks/overview'); tt = (r[1] or {}).get('totals', {})
ok(r[0] == 200 and tt.get('stocks') == 7, 'Tableau de bord des stocks (/api/stocks/overview)', err(r)); info(f"{tt.get('linked')}/7 liés, {tt.get('articles')} article(s), {tt.get('units')} unité(s), {tt.get('low_items')} sous le seuil, {tt.get('pending_transfers')} transfert(s) en attente")
if (r[1] or {}).get('error'): ok(False, 'Lecture GLPI pour le tableau de bord', r[1]['error'])

title('5. Assistant IA et agents')
r = a.call('POST', '/api/assistant/chat', {'message': 'Bonjour'}, timeout=180); ok(r[0] == 200 and (r[1] or {}).get('answer'), 'Assistant IA répond', err(r))
r = a.call('POST', '/api/assistant/chat', {'message': 'Où en sont mes tickets ? Utilise tes outils.'}, timeout=180)
if ok(r[0] == 200 and (r[1] or {}).get('answer'), 'Assistant connecté: question sur les tickets', err(r)):
    used = (r[1] or {}).get('tools_used', []); print('           « ' + r[1]['answer'].replace('\n', ' ')[:260] + ' »')
    if 'list_my_tickets' in used: ok(True, "L'assistant a lu les tickets dans GLPI (outil list_my_tickets)")
    else: info("Le modèle n'a pas appelé l'outil tickets: lisez sa réponse ci-dessus; essayez AI_MODEL=openai/gpt-oss-120b")
r = a.call('POST', '/api/assistant/chat', {'message': 'Mon imprimante ne marche plus, crée-moi un ticket.'}, timeout=180)
if ok(r[0] == 200, 'Assistant connecté: demande de ticket', err(r)):
    d = (r[1] or {}).get('ticket_draft')
    if d: ok(True, 'Brouillon de ticket proposé (rien créé tant que vous ne confirmez pas)'); info('Brouillon: ' + d['title'])
    else: info("Pas de brouillon cette fois (le modèle a répondu en texte): réessayez dans l'onglet Assistant IA")
for agent, q in (('STOCK-01', "Quel est l'état de mon stock ? Donne les articles et les quantités."), ('ADMIN', "Donne l'état de tous les stocks.")):
    r = a.call('POST', '/api/agents/chat', {'agent': agent, 'message': q}, timeout=180); ans = (r[1] or {}).get('answer', '')
    if ok(r[0] == 200 and ans, f'Agent {agent} répond', err(r)):
        print('           « ' + ans.replace('\n', ' ')[:300] + (' … »' if len(ans) > 300 else ' »'))
        if item and agent == 'STOCK-01':
            if item['name'] in ans: ok(True, "L'agent a lu les vrais articles dans GLPI (il cite l'article de test)")
            else: info("L'agent ne cite pas l'article de test: vérifiez à l'oeil que sa réponse correspond à l'état réel de STOCK-01")

title('6. Isolation des comptes')
if ask("Créer/utiliser le compte 'selftest_user' (magasinier STOCK-02) pour tester les droits ?"):
    tpw = 'Test_' + secrets.token_urlsafe(12)
    r = a.call('POST', '/api/admin/users', {'username': 'selftest_user', 'password': tpw, 'role': 'user', 'stock_entity_code': 'STOCK-02'})
    if r[0] == 400:
        uid = next((u['id'] for u in (a.call('GET', '/api/admin/users')[1] or {}).get('users', []) if u['username'] == 'selftest_user'), None)
        r = a.call('POST', '/api/admin/users/update', {'id': uid, 'password': tpw, 'role': 'user', 'stock_entity_code': 'STOCK-02'})
    if r[0] in (200, 201): test_user_id = next((u['id'] for u in (a.call('GET', '/api/admin/users')[1] or {}).get('users', []) if u['username'] == 'selftest_user'), None)
    if ok(r[0] in (200, 201), 'Compte magasinier de test prêt', err(r)):
        b = Client(); ok(b.call('POST', '/api/auth/login', {'username': 'selftest_user', 'password': tpw})[0] == 200, 'Connexion du magasinier')
        ok(b.call('GET', '/api/stock/items?code=STOCK-01')[0] == 403, 'Refus: lire les articles d\'un autre stock')
        ok(b.call('POST', '/api/agents/chat', {'agent': 'STOCK-01', 'message': 'stock'})[0] == 403, 'Refus: parler à l\'agent d\'un autre stock')
        ok(b.call('POST', '/api/agents/chat', {'agent': 'ADMIN', 'message': 'stock'})[0] == 403, 'Refus: parler à l\'agent ADMIN')
        ok(b.call('POST', '/api/agents/round', {})[0] == 403, 'Refus: lancer la ronde'); ok(b.call('POST', '/api/transfers/decide', {'id': 1, 'decision': 'approve'})[0] == 403, 'Refus: approuver un transfert')
        ok(b.call('GET', '/api/stock/items?code=STOCK-02')[0] != 403, 'Accès autorisé à SON stock (STOCK-02)')
else: info('Étape ignorée')

title('7. Ronde des agents (utilise votre quota IA)')
if ask('Lancer la ronde des agents ?'):
    r = a.call('POST', '/api/agents/round', {}, timeout=400); rep = (r[1] or {}).get('report', [])
    if ok(r[0] == 200, 'Ronde terminée', err(r)):
        for line in rep: print('           ' + line.replace('\n', ' ')[:240])
        ok(not any('ERREUR' in x for x in rep), 'Aucun agent en erreur', 'voir les lignes ERREUR ci-dessus (limite de débit: attendez 1 minute)')
    t = (a.call('GET', '/api/transfers')[1] or {}).get('transfers', []); info(f"{sum(1 for x in t if x['status'] == 'pending')} transfert(s) en attente: approuvez-les dans l'onglet Agents")
    m = (a.call('GET', '/api/agents/inbox?agent=ADMIN')[1] or {}).get('messages', []); info(f'{len(m)} message(s) dans la boîte ADMIN')
else: info('Étape ignorée')

title('8. Journal, export, suivi des tickets, sauvegarde')
if item:
    kinds = [m['kind'] for m in (a.call('GET', '/api/stock/movements?code=STOCK-01&limit=50')[1] or {}).get('movements', []) if m['item_name'].startswith('ZZ-AutoTest-')]
    ok({'create', 'entry'} <= set(kinds), 'Journal des mouvements: création et entrée enregistrées', f'types vus: {kinds}')
    c, body, ct = a.raw('/api/stock/export.csv?kind=stock&code=STOCK-01'); ok(c == 200 and 'csv' in ct and item['name'].encode() in body, 'Export CSV du stock (contient l\'article de test)', f'statut {c}')
    c, body, ct = a.raw('/api/stock/export.csv?kind=movements&code=STOCK-01'); ok(c == 200 and 'csv' in ct, 'Export CSV du journal', f'statut {c}')
if tid_test:
    r = a.call('POST', '/api/ticket/followup', {'ticket_id': tid_test, 'content': 'Commentaire de test (selftest)'}); ok(r[0] == 201, 'Ajout d\'un commentaire (suivi) dans GLPI', err(r))
    r = a.call('GET', f'/api/ticket/detail?id={tid_test}'); fl = (r[1] or {}).get('followups', []); ok(r[0] == 200 and any('selftest' in f['content'] for f in fl), 'Détail du ticket: le commentaire apparaît', err(r) if r[0] != 200 else f'{len(fl)} suivi(s) lus')
else: info('Ticket de test absent: test du suivi ignoré (acceptez la création d\'un ticket à l\'étape 3)')
r = a.call('POST', '/api/admin/backup', {}); ok(r[0] == 201 and (r[1] or {}).get('file'), 'Sauvegarde de la base créée', err(r))
r = a.call('GET', '/api/admin/activity?limit=5'); ok(r[0] == 200 and len((r[1] or {}).get('events', [])) > 0, 'Journal d\'activité lisible', err(r))

r = a.call('GET', '/api/stock/insights'); sm = (r[1] or {}).get('summary', {}); ok(r[0] == 200 and isinstance((r[1] or {}).get('rows'), list), 'Prévisions de stock et liste de commande', err(r)); info(f"{sm.get('critical')} critique(s), {sm.get('soon')} à surveiller, {sm.get('to_order_units')} unité(s) conseillée(s) à commander")
c, body, ct = a.raw('/api/stock/export.csv?kind=reorder'); ok(c == 200 and 'csv' in ct, 'Export CSV de la liste de commande', f'statut {c}')

title('8b. Réglages d\'automatisation')
r = a.call('GET', '/api/admin/settings'); cfg = (r[1] or {}).get('settings', {})
if ok(r[0] == 200 and 'auto_max_qty' in cfg, 'Lecture des réglages', err(r)):
    info(f"approbation auto jusqu'à {cfg['auto_max_qty']} unité(s) | ronde auto toutes les {cfg['round_interval_min']} min (0 = désactivé)")
    r = a.call('POST', '/api/admin/settings', {'auto_max_qty': int(cfg['auto_max_qty'] or 0), 'auto_glpi_user_id': cfg['auto_glpi_user_id'], 'round_interval_min': int(cfg['round_interval_min'] or 0)}); ok(r[0] == 200, 'Enregistrement des mêmes réglages (aller-retour)', err(r))
    ok(a.call('POST', '/api/admin/settings', {'auto_max_qty': 99})[0] == 400, 'Valeur dangereuse refusée (approbation auto > 50)')

title('9. Nettoyage')
if item:
    r = a.call('POST', '/api/stock/items/delete', {'code': 'STOCK-01', 'item_id': item['id']})
    if ok(r[0] == 200 and not any(i['id'] == item['id'] for i in (r[1] or {}).get('items', [])), "Article de test supprimé (corbeille GLPI)", err(r)): item = None
if test_user_id is not None:
    ok(a.call('POST', '/api/admin/users/delete', {'id': test_user_id})[0] == 200, "Compte 'selftest_user' supprimé"); test_user_id = None

print(f'\n==== Résultat: {passed} réussi(s), {failed} échec(s) ====')
if item: print(f"À nettoyer dans GLPI (Gestion > Consommables): l'article {item['name']} (STOCK-01).")
if test_user_id is not None: print("À supprimer: compte selftest_user (Administration > Comptes).")
sys.exit(1 if failed else 0)
