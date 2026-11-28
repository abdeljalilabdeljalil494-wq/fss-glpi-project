"""Tests des fonctions stock / agents / tickets (GLPI simulé en mémoire, IA simulée)."""
import io, itertools, json, os, re, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
os.environ['APP_ENV_FILE'] = '/nonexistent.env'
os.environ['APP_SECRET_KEY'] = 'x' * 48
import app as module

_ip = itertools.count(1)

class FakeGlpi:
    """Imite les parties de l'API REST GLPI utilisées par l'application."""
    def __init__(s):
        s.ent = [{'id': 0, 'name': 'Root', 'completename': 'Root', 'entities_id': None}]; s.items = []; s.cons = []; s.fu = []; s.sol = []
        s.cats = [{'id': 1, 'name': 'Réseau', 'completename': 'Réseau', 'is_helpdeskvisible': 1}, {'id': 2, 'name': 'Interne', 'completename': 'Interne', 'is_helpdeskvisible': 0}, {'id': 3, 'name': 'Imprimantes', 'completename': 'Matériel > Imprimantes', 'is_helpdeskvisible': 1}]; s.created = []
        s.tickets = {101: {'id': 101, 'name': 'Imprimante', 'status': 1, 'users_id_recipient': 5, 'content': '&lt;p&gt;desc&lt;/p&gt;', 'date': '2026-11-10'}}
    def _page(s, lst, path):
        m = re.search(r'range=(\d+)-(\d+)', path); a, b = (int(m.group(1)), int(m.group(2))) if m else (0, 199); return lst[a:b + 1]
    def __call__(s, method, path, payload=None):
        base = path.split('?')[0]; inp = (payload or {}).get('input')
        if method == 'GET' and base == '/Entity': return s._page(s.ent, path)
        if method == 'GET' and base == '/ITILCategory': return s._page(s.cats, path)
        if method == 'POST' and base == '/Ticket': s.created.append(inp); return {'id': 200 + len(s.created)}
        if method == 'POST' and base == '/Entity': i = len(s.ent) + 5; s.ent.append({'id': i, 'name': inp['name'], 'completename': 'Root > ' + inp['name'], 'entities_id': inp.get('entities_id')}); return {'id': i}
        if method == 'GET' and base == '/ConsumableItem': return s._page(s.items, path)
        if method == 'GET' and base == '/Consumable': return s._page(s.cons, path)
        if method == 'POST' and base == '/ConsumableItem': i = len(s.items) + 1; s.items.append({'id': i, **inp}); return {'id': i}
        if method == 'POST' and base == '/Consumable':
            for u in (inp if isinstance(inp, list) else [inp]): s.cons.append({'id': len(s.cons) + 1, 'consumableitems_id': u['consumableitems_id'], 'entities_id': u['entities_id'], 'date_out': None})
            return [{'id': 1}]
        if method == 'PUT' and base == '/Consumable':
            for u in inp:
                for c in s.cons:
                    if c['id'] == u['id']: c.update(itemtype=u['itemtype'], items_id=u['items_id'], date_out=u['date_out'])
            return [{}]
        m = re.match(r'/ConsumableItem/(\d+)$', base)
        if m and method == 'PUT': next(i for i in s.items if i['id'] == int(m.group(1))).update(inp); return [{}]
        if m and method == 'DELETE': s.items = [i for i in s.items if i['id'] != int(m.group(1))]; return [{}]
        m = re.match(r'/Ticket/(\d+)(/ITILFollowup|/ITILSolution)?$', base)
        if m:
            t = s.tickets.get(int(m.group(1)))
            if not t: raise module.AppError(404, 'GLPI resource not found')
            if m.group(2) == '/ITILFollowup': return [f for f in s.fu if f['items_id'] == t['id']]
            if m.group(2) == '/ITILSolution': return [f for f in s.sol if f['items_id'] == t['id']]
            if method == 'PUT': t.update(inp); return [{}]
            return dict(t)
        if method == 'POST' and base == '/ITILFollowup': s.fu.append({**inp, 'id': len(s.fu) + 1, 'users_id': 'glpi', 'date': '2026-11-14 10:00:00'}); return {'id': 1}
        if method == 'POST' and base == '/ITILSolution': s.sol.append({**inp, 'date_creation': '2026-11-14 12:00:00'}); s.tickets[inp['items_id']]['status'] = 5; return {'id': 1}
        raise AssertionError(f'appel GLPI non prévu: {method} {path}')

class FeatureTest(unittest.TestCase):
    def setUp(self):
        module._RATE.clear(); module._CAT.update(t=0.0, v=[]); self.tmp = tempfile.TemporaryDirectory(); self.old = module.DB; module.DB = Path(self.tmp.name) / 't.sqlite3'; module.init_db()
        self.glpi = FakeGlpi(); self.ip = f'10.0.{next(_ip)}.1'
        self.patches = [patch('app.glpi_request', self.glpi), patch.dict(os.environ, {'APP_SECRET_KEY': 'x' * 48, 'ALLOW_ADMIN_SETUP': 'true'})]
        for p in self.patches: p.start()
        self.admin = self.api('/api/auth/setup', 'POST', {'username': 'boss', 'password': 'A_secure_test_password!'}, '')[2]
        self.api('/api/admin/users/update', 'POST', {'id': 1, 'glpi_user_id': '2'}, self.admin)
        self.api('/api/admin/entities/sync', 'POST', {}, self.admin)
    def tearDown(self):
        for p in self.patches: p.stop()
        module.DB = self.old; self.tmp.cleanup()
    def api(self, path, method='GET', data=None, cookie=''):
        raw = json.dumps(data or {}).encode(); qs = ''
        if '?' in path: path, qs = path.split('?', 1)
        env = {'PATH_INFO': path, 'QUERY_STRING': qs, 'REQUEST_METHOD': method, 'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw), 'HTTP_COOKIE': cookie, 'REMOTE_ADDR': self.ip}; cap = {}
        body = b''.join(module.app(env, lambda s, h: cap.update(status=s, headers=dict(h)))); code = int(cap['status'].split()[0])
        ck = cap['headers'].get('Set-Cookie', '').split(';', 1)[0]
        try: return code, json.loads(body), ck
        except ValueError: return code, body, ck
    def raw(self, path, method='GET', headers=None, body=b'', remote='127.0.0.1'):
        env = {'PATH_INFO': path, 'QUERY_STRING': '', 'REQUEST_METHOD': method, 'CONTENT_LENGTH': str(len(body)), 'wsgi.input': io.BytesIO(body), 'REMOTE_ADDR': remote, **(headers or {})}; cap = {}
        out = b''.join(module.app(env, lambda s, h: cap.update(status=s, headers=dict(h))))
        return int(cap['status'].split()[0]), cap['headers'], out

    # ---- mise en production derrière un reverse proxy HTTPS ----
    def test_security_headers_on_page_static_and_api_and_hsts_only_in_production(self):
        need = ('Content-Security-Policy', 'X-Frame-Options', 'X-Content-Type-Options', 'Referrer-Policy')
        for path in ('/', '/static/app.js', '/api/health'):
            c, h, _ = self.raw(path); self.assertEqual(c, 200, path)
            for k in need: self.assertIn(k, h, f'{k} manquant sur {path}')
        self.assertNotIn('Strict-Transport-Security', self.raw('/')[1])
        with patch.dict(os.environ, {'APP_ENV': 'production'}): self.assertIn('Strict-Transport-Security', self.raw('/')[1])
    def test_client_ip_trusts_the_proxy_only_when_enabled_and_only_from_loopback(self):
        e = {'REMOTE_ADDR': '127.0.0.1', 'HTTP_X_FORWARDED_FOR': '6.6.6.6, 10.1.2.3'}
        self.assertEqual(module.client_ip(e), '127.0.0.1')  # option désactivée
        with patch.dict(os.environ, {'TRUST_PROXY': 'true'}):
            self.assertEqual(module.client_ip(e), '10.1.2.3')  # dernière entrée = celle ajoutée par notre proxy (6.6.6.6 est falsifiable)
            self.assertEqual(module.client_ip({**e, 'REMOTE_ADDR': '192.168.1.9'}), '192.168.1.9')  # un client direct ne peut pas se faire passer pour un autre
    def test_origin_check_works_behind_a_proxy_and_still_rejects_foreign_sites(self):
        h = {'HTTP_HOST': '127.0.0.1:8000', 'HTTP_ORIGIN': 'https://portail.fss.tn', 'HTTP_X_FORWARDED_HOST': 'portail.fss.tn'}; body = json.dumps({'username': 'x', 'password': 'y'}).encode()
        self.assertEqual(self.raw('/api/auth/login', 'POST', h, body)[0], 403)  # proxy non déclaré de confiance
        with patch.dict(os.environ, {'TRUST_PROXY': 'true'}):
            self.assertEqual(self.raw('/api/auth/login', 'POST', h, body)[0], 401)  # origine acceptée, identifiants refusés
            self.assertEqual(self.raw('/api/auth/login', 'POST', {**h, 'HTTP_ORIGIN': 'https://evil.example'}, body)[0], 403)
    def test_login_is_throttled_per_account_without_blocking_other_accounts(self):
        for _ in range(6): self.assertEqual(self.api('/api/auth/login', 'POST', {'username': 'boss', 'password': 'bad'}, '')[0], 401)
        self.assertEqual(self.api('/api/auth/login', 'POST', {'username': 'boss', 'password': 'bad'}, '')[0], 429)
        self.assertEqual(self.api('/api/auth/login', 'POST', {'username': 'other', 'password': 'bad'}, '')[0], 401)
    def test_many_users_behind_one_proxy_are_not_locked_out_together(self):
        with patch.dict(os.environ, {'TRUST_PROXY': 'true'}):
            for i in range(14): self.assertEqual(self.raw('/api/auth/login', 'POST', {'HTTP_X_FORWARDED_FOR': f'10.9.0.{i}', 'HTTP_HOST': 'h'}, json.dumps({'username': f'u{i}', 'password': 'x'}).encode())[0], 401)

    def user(self, name, stock, glpi_id='5'):
        self.api('/api/admin/users', 'POST', {'username': name, 'password': 'Magasin_password_12!', 'role': 'user', 'stock_entity_code': stock, 'glpi_user_id': glpi_id}, self.admin)
        return self.api('/api/auth/login', 'POST', {'username': name, 'password': 'Magasin_password_12!'}, '')[2]
    def item(self, code, name, qty, th=5):
        c, b, _ = self.api('/api/stock/items', 'POST', {'code': code, 'name': name, 'quantity': qty, 'threshold': th}, self.admin); self.assertEqual(c, 201, b)
        return next(i['id'] for i in b['items'] if i['name'] == name)
    def qty(self, code, name):
        return next(i['quantity'] for i in self.api('/api/stock/items?code=' + code, 'GET', None, self.admin)[1]['items'] if i['name'] == name)

    def test_entity_sync_creates_the_seven_entities_in_glpi(self):
        self.assertEqual(len([e for e in self.glpi.ent if e['id'] != 0]), 7)
        c, b, _ = self.api('/api/admin/entities/sync', 'POST', {}, self.admin); self.assertEqual(len(b['report']['already_ok']), 7)  # idempotent
    def test_stock_flow_and_movement_journal(self):
        i = self.item('STOCK-01', 'Papier A4', 5, 6); self.assertTrue(self.api('/api/stock/items?code=STOCK-01', 'GET', None, self.admin)[1]['items'][0]['low'])
        self.api('/api/stock/entry', 'POST', {'code': 'STOCK-01', 'item_id': i, 'quantity': 3}, self.admin); self.assertEqual(self.qty('STOCK-01', 'Papier A4'), 8)
        self.api('/api/stock/exit', 'POST', {'code': 'STOCK-01', 'item_id': i, 'quantity': 2}, self.admin); self.assertEqual(self.qty('STOCK-01', 'Papier A4'), 6)
        kinds = [m['kind'] for m in self.api('/api/stock/movements?code=STOCK-01', 'GET', None, self.admin)[1]['movements']]; self.assertEqual(kinds, ['exit', 'entry', 'create'])
    def test_exit_refused_when_not_enough_units(self):
        i = self.item('STOCK-01', 'Stylos', 3); self.assertEqual(self.api('/api/stock/exit', 'POST', {'code': 'STOCK-01', 'item_id': i, 'quantity': 10}, self.admin)[0], 400)
        self.assertEqual(self.qty('STOCK-01', 'Stylos'), 3)
    def test_storekeeper_is_confined_to_own_stock(self):
        self.item('STOCK-01', 'Papier A4', 5); ck = self.user('mag2', 'STOCK-02')
        self.assertEqual(self.api('/api/stock/items?code=STOCK-01', 'GET', None, ck)[0], 403)
        self.assertEqual(self.api('/api/stock/movements?code=STOCK-01', 'GET', None, ck)[0], 403)
        self.assertEqual(self.api('/api/agents/chat', 'POST', {'agent': 'STOCK-01', 'message': 'stock'}, ck)[0], 403)
        self.assertEqual(self.api('/api/agents/chat', 'POST', {'agent': 'ADMIN', 'message': 'stock'}, ck)[0], 403)
        self.assertEqual(self.api('/api/agents/round', 'POST', {}, ck)[0], 403); self.assertEqual(self.api('/api/admin/users', 'GET', None, ck)[0], 403)
        self.assertEqual([s['code'] for s in self.api('/api/stocks/overview', 'GET', None, ck)[1]['stocks']], ['STOCK-02'])
    def test_transfer_needs_human_approval_and_moves_units(self):
        self.item('STOCK-01', 'Papier A4', 3); self.item('STOCK-02', 'Papier A4', 40)
        tid = module.propose_transfer('STOCK-02', 'STOCK-01', 'papier a4', 10, 1)
        self.assertEqual(self.qty('STOCK-02', 'Papier A4'), 40)  # rien ne bouge avant approbation
        self.assertEqual(self.api('/api/transfers/decide', 'POST', {'id': tid, 'decision': 'approve'}, self.user('mag', 'STOCK-01'))[0], 403)
        self.assertEqual(self.api('/api/transfers/decide', 'POST', {'id': tid, 'decision': 'approve'}, self.admin)[0], 200)
        self.assertEqual((self.qty('STOCK-02', 'Papier A4'), self.qty('STOCK-01', 'Papier A4')), (30, 13))
        self.assertEqual(self.api('/api/transfers/decide', 'POST', {'id': tid, 'decision': 'approve'}, self.admin)[0], 400)  # pas de double exécution
    def test_auto_approval_guard_rails(self):
        self.item('STOCK-01', 'Papier A4', 3); self.item('STOCK-02', 'Papier A4', 40); self.item('STOCK-03', 'Papier A4', 8)
        self.assertEqual(self.api('/api/admin/settings', 'POST', {'auto_max_qty': 10, 'auto_glpi_user_id': '', 'round_interval_min': 0}, self.admin)[0], 400)  # id GLPI obligatoire
        self.assertEqual(self.api('/api/admin/settings', 'POST', {'auto_max_qty': 10, 'auto_glpi_user_id': '2', 'round_interval_min': 0}, self.admin)[0], 200)
        t = lambda f, to, q: module.maybe_auto_approve(module.propose_transfer(f, to, 'Papier A4', q, 1))
        self.assertEqual(t('STOCK-02', 'STOCK-01', 10), 'approved'); self.assertEqual(self.qty('STOCK-02', 'Papier A4'), 30)
        self.assertEqual(t('STOCK-02', 'STOCK-01', 15), 'pending')   # au-dessus de la limite
        self.assertEqual(t('STOCK-03', 'STOCK-01', 4), 'pending')    # laisserait la source sous son seuil (8-4 < 5)
        self.api('/api/admin/settings', 'POST', {'auto_max_qty': 0, 'auto_glpi_user_id': '2', 'round_interval_min': 0}, self.admin); self.assertEqual(t('STOCK-02', 'STOCK-01', 2), 'pending')
    def test_settings_validation(self):
        for bad in ({'auto_max_qty': 99}, {'auto_max_qty': -1}, {'round_interval_min': 5}, {'round_interval_min': 5000}, {'auto_glpi_user_id': 'abc'}):
            self.assertEqual(self.api('/api/admin/settings', 'POST', bad, self.admin)[0], 400, bad)
    def test_ticket_status_is_admin_only_logged_and_verified(self):
        ck = self.user('simple', None)
        self.assertEqual(self.api('/api/admin/tickets/status', 'POST', {'ticket_id': 101, 'status': 2}, ck)[0], 403)
        self.assertEqual(self.api('/api/admin/tickets/status', 'POST', {'ticket_id': 101, 'status': 9}, self.admin)[0], 400)
        c, b, _ = self.api('/api/admin/tickets/status', 'POST', {'ticket_id': 101, 'status': 4, 'comment': 'attente budget'}, self.admin); self.assertEqual((c, b['status']), (200, 4))
        self.assertEqual(self.api('/api/admin/tickets/status', 'POST', {'ticket_id': 101, 'status': 4}, self.admin)[0], 400)  # déjà dans cet état
        self.api('/api/admin/tickets/status', 'POST', {'ticket_id': 101, 'status': 5}, self.admin); self.assertEqual(len(self.glpi.sol), 1)  # Résolu => solution GLPI
        ev = self.api('/api/admin/tickets/history?ticket_id=101', 'GET', None, self.admin)[1]['events']; self.assertEqual([(e['from_status'], e['to_status']) for e in ev], [(4, 5), (1, 4)])
    def test_ticket_detail_scope_and_private_followups(self):
        self.glpi.fu += [{'id': 1, 'items_id': 101, 'content': 'public', 'users_id': 'tech', 'date': '2026-11-11', 'is_private': 0}, {'id': 2, 'items_id': 101, 'content': 'note interne', 'users_id': 'tech', 'date': '2026-11-12', 'is_private': 1}]
        owner = self.user('owner', None, '5'); other = self.user('other', None, '9')
        self.assertEqual(self.api('/api/ticket/detail?id=101', 'GET', None, other)[0], 404)  # pas son ticket
        texts = [f['content'] for f in self.api('/api/ticket/detail?id=101', 'GET', None, owner)[1]['followups']]; self.assertEqual(texts, ['public'])
        self.assertEqual(len(self.api('/api/ticket/detail?id=101', 'GET', None, self.admin)[1]['followups']), 2)
    def test_followup_is_escaped_and_attributed(self):
        owner = self.user('owner', None, '5'); self.assertEqual(self.api('/api/ticket/followup', 'POST', {'ticket_id': 101, 'content': '<script>alert(1)</script>'}, owner)[0], 201)
        self.assertNotIn('<script>', self.glpi.fu[0]['content']); d = self.api('/api/ticket/detail?id=101', 'GET', None, owner)[1]['followups'][0]; self.assertEqual(d['author'], 'owner · portail')
        self.assertEqual(self.api('/api/ticket/followup', 'POST', {'ticket_id': 101, 'content': 'x'}, owner)[0], 400)
    def test_password_change(self):
        self.assertEqual(self.api('/api/auth/password', 'POST', {'current': 'faux', 'new': 'Another_password_123'}, self.admin)[0], 400)
        self.assertEqual(self.api('/api/auth/password', 'POST', {'current': 'A_secure_test_password!', 'new': 'court'}, self.admin)[0], 400)
        self.assertEqual(self.api('/api/auth/password', 'POST', {'current': 'A_secure_test_password!', 'new': 'Another_password_123'}, self.admin)[0], 200)
        self.assertEqual(self.api('/api/auth/login', 'POST', {'username': 'boss', 'password': 'A_secure_test_password!'}, '')[0], 401)
        self.assertEqual(self.api('/api/auth/login', 'POST', {'username': 'boss', 'password': 'Another_password_123'}, '')[0], 200)
    def test_csv_export_neutralises_formulas(self):
        self.item('STOCK-01', '=HYPERLINK("http://x")', 2); c, b, _ = self.api('/api/stock/export.csv?kind=stock', 'GET', None, self.admin)
        txt = b.decode('utf-8'); self.assertEqual(c, 200); self.assertIn("'=HYPERLINK", txt); self.assertTrue(txt.startswith('\ufeffStock;'))
        self.assertEqual(self.api('/api/stock/export.csv?kind=nope', 'GET', None, self.admin)[0], 400)
    def test_backup_creates_a_readable_copy(self):
        c, b, _ = self.api('/api/admin/backup', 'POST', {}, self.admin); self.assertEqual(c, 201)
        import sqlite3; con = sqlite3.connect(str(module.DB.parent / 'backups' / b['file'])); self.assertEqual(con.execute('select count(*) from users').fetchone()[0], 1); con.close()
        self.assertEqual(self.api('/api/admin/backup', 'POST', {}, self.user('mag', 'STOCK-01'))[0], 403)
    def test_assistant_status_change_is_a_proposal_for_admins_only(self):
        call = {'id': 'c1', 'type': 'function', 'function': {'name': 'propose_status_change', 'arguments': json.dumps({'ticket_id': 101, 'status': 4, 'comment': 'bloqué'})}}
        script = lambda: iter([{'content': None, 'tool_calls': [call]}, {'content': 'Je prépare le changement.'}])
        with patch('app.ai_chat', side_effect=script()):
            c, b, _ = self.api('/api/assistant/chat', 'POST', {'message': 'mets le ticket 101 en bloqué'}, self.admin)
        self.assertEqual(b['status_draft']['status'], 4); self.assertEqual(self.glpi.tickets[101]['status'], 1)  # rien modifié sans confirmation
        with patch('app.ai_chat', side_effect=script()):
            c, b, _ = self.api('/api/assistant/chat', 'POST', {'message': 'mets le ticket 101 en bloqué'}, self.user('simple', None))
        self.assertNotIn('status_draft', b)
    def test_agent_tools_cannot_cross_stocks(self):
        self.item('STOCK-01', 'Papier A4', 3); self.item('STOCK-02', 'Colle', 9)
        r = module.exec_tool('STOCK-02', 'get_my_stock', {}, {'id': 1, 'role': 'admin'}); self.assertEqual([i['name'] for i in r['items']], ['Colle'])
        self.assertIn('error', module.exec_tool('STOCK-02', 'get_all_stock', {}, {'id': 1, 'role': 'admin'}))  # outil réservé à l'agent ADMIN
        self.assertEqual(module.exec_tool('STOCK-02', 'propose_transfer', {'to_code': 'STOCK-02', 'item_name': 'Colle', 'quantity': 1}, None).get('error'), 'Invalid destination stock')

    # ---- v4: tickets enrichis, prévisions de stock, liste de commande ----
    def test_ticket_creation_forwards_type_urgency_category_and_place(self):
        c, b, _ = self.api('/api/tickets', 'POST', {'name': 'Projecteur HS', 'content': 'Ne s allume plus', 'type': '2', 'urgency': '4', 'category_id': '3', 'place': 'Labo 1'}, self.admin); self.assertEqual(c, 201, b)
        i = self.glpi.created[0]; self.assertEqual((i['type'], i['urgency'], i['itilcategories_id']), (2, 4, 3)); self.assertTrue(i['content'].startswith('Lieu : Labo 1'))
        self.api('/api/tickets', 'POST', {'name': 'Simple', 'content': 'sans options'}, self.admin); self.assertNotIn('urgency', self.glpi.created[1])  # rétrocompatible
    def test_ticket_creation_rejects_out_of_range_values(self):
        for bad in ({'urgency': '9'}, {'urgency': 'haute'}, {'type': '3'}, {'category_id': '0'}):
            self.assertEqual(self.api('/api/tickets', 'POST', {'name': 'Titre valide', 'content': 'contenu valide', **bad}, self.admin)[0], 400, bad)
        self.assertEqual(self.glpi.created, [])
    def test_ticket_options_lists_helpdesk_categories_only_and_degrades_gracefully(self):
        names = [c['name'] for c in self.api('/api/ticket/options', 'GET', None, self.admin)[1]['categories']]; self.assertEqual(names, ['Matériel > Imprimantes', 'Réseau'])  # catégorie interne masquée, tri alphabétique
        module._CAT.update(t=0.0, v=[])
        with patch('app.glpi_request', side_effect=module.AppError(503, 'GLPI is unreachable')):
            c, b, _ = self.api('/api/ticket/options', 'GET', None, self.admin); self.assertEqual((c, b['categories']), (200, []))
    def _history(self, code, name, exits, first_days=20):
        with module.db() as c:
            c.execute("INSERT INTO stock_movements(user_id,stock_code,item_name,kind,qty,created_at) VALUES(1,?,?,'create',0,datetime('now',?))", (code, name, f'-{first_days} days'))
            for d, q in exits: c.execute("INSERT INTO stock_movements(user_id,stock_code,item_name,kind,qty,created_at) VALUES(1,?,?,'exit',?,datetime('now',?))", (code, name, q, f'-{d} days'))
    def test_insights_estimate_days_left_and_suggested_order(self):
        self.item('STOCK-01', 'Papier', 9); self.item('STOCK-01', 'Colle', 2); self.item('STOCK-01', 'Stylos', 100)
        self._history('STOCK-01', 'Papier', [(10, 10), (6, 10), (2, 10)])  # 30 sorties sur 20 jours = 1,5 / jour
        c, b, _ = self.api('/api/stock/insights', 'GET', None, self.admin); rows = {r['article']: r for r in b['rows']}
        p = rows['Papier']; self.assertEqual((p['priority'], p['days_left'], p['consumption_30d'], p['reliable']), ('critical', 6.0, 30, True)); self.assertEqual(p['suggested_order'], 41)  # ceil(1,5*30)+5-9
        k = rows['Colle']; self.assertEqual((k['priority'], k['days_left'], k['suggested_order']), ('soon', None, 8))  # sous le seuil, sans historique: viser 2 x seuil
        self.assertEqual((rows['Stylos']['priority'], rows['Stylos']['suggested_order']), ('ok', 0))
        self.assertEqual([r['article'] for r in b['rows']], ['Papier', 'Colle', 'Stylos']); self.assertEqual((b['summary']['critical'], b['summary']['soon'], b['summary']['to_order_units']), (1, 1, 49))
    def test_insights_flags_soon_when_under_two_weeks_even_above_the_threshold(self):
        self.item('STOCK-01', 'Encre', 15, 5); self._history('STOCK-01', 'Encre', [(10, 10), (6, 10), (2, 10)])  # 1,5 / jour, reste 10 jours, mais 15 > seuil 5
        r = self.api('/api/stock/insights?code=STOCK-01', 'GET', None, self.admin)[1]['rows'][0]; self.assertEqual((r['priority'], r['days_left']), ('soon', 10.0)); self.assertFalse(r['quantity'] <= r['threshold'])
    def test_insights_window_is_damped_for_a_young_stock(self):
        self.item('STOCK-01', 'Papier', 10); self._history('STOCK-01', 'Papier', [(0, 14)], first_days=1)  # 14 sorties le jour même ne doivent pas valoir 14 / jour
        r = self.api('/api/stock/insights?code=STOCK-01', 'GET', None, self.admin)[1]['rows'][0]; self.assertEqual(r['days_left'], 5.0); self.assertFalse(r['reliable'])  # 14 / 7 jours = 2 par jour
    def test_insights_scope_and_reorder_csv(self):
        self.item('STOCK-01', 'Papier', 9); self.item('STOCK-01', 'Stylos', 100); self.item('STOCK-02', 'Craie', 50); self._history('STOCK-01', 'Papier', [(10, 10), (6, 10), (2, 10)])
        ck = self.user('mag2', 'STOCK-02')
        self.assertEqual(self.api('/api/stock/insights?code=STOCK-01', 'GET', None, ck)[0], 403)
        self.assertEqual([r['stock'] for r in self.api('/api/stock/insights', 'GET', None, ck)[1]['rows']], ['STOCK-02'])
        c, body, _ = self.api('/api/stock/export.csv?kind=reorder', 'GET', None, self.admin); txt = body.decode('utf-8')
        self.assertEqual(c, 200); self.assertIn('Papier', txt); self.assertIn('Critique', txt); self.assertIn(';6,0;', txt); self.assertNotIn('Stylos', txt); self.assertNotIn('Craie', txt)  # seuls les articles à commander
        self.assertEqual(self.api('/api/stock/export.csv?kind=reorder&code=STOCK-01', 'GET', None, ck)[0], 403)
    def test_assistant_ticket_draft_keeps_a_valid_urgency_only(self):
        def call(u): return {'id': 'c', 'type': 'function', 'function': {'name': 'propose_ticket', 'arguments': json.dumps({'title': 'Wifi coupé', 'description': 'Plus de réseau en salle 3', 'urgency': u})}}
        for urg, expected in ((4, 4), (9, None)):
            with patch('app.ai_chat', side_effect=iter([{'content': None, 'tool_calls': [call(urg)]}, {'content': 'ok'}])):
                b = self.api('/api/assistant/chat', 'POST', {'message': 'wifi'}, self.admin)[1]
            self.assertEqual(b['ticket_draft'].get('urgency'), expected)

if __name__ == '__main__': unittest.main()
