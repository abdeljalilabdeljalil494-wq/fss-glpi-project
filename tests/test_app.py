import io, json, os, tempfile, unittest
from unittest.mock import patch
os.environ['APP_ENV_FILE']='/nonexistent.env'
os.environ['APP_SECRET_KEY']='x'*48
from app import app, DB, init_db

class ApiTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.old=DB
  import app as module; module.DB=__import__('pathlib').Path(self.tmp.name)/'t.sqlite3'; init_db()
 def tearDown(self):
  import app as module; module.DB=self.old; self.tmp.cleanup()
 def request(self,path,method='GET',data=None,cookie=''):
  raw=json.dumps(data or {}).encode(); environ={'PATH_INFO':path,'REQUEST_METHOD':method,'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),'HTTP_COOKIE':cookie,'CONTENT_TYPE':'application/json'}; captured={}
  def start(status,headers):captured.update(status=status,headers=dict(headers))
  body=b''.join(app(environ,start)); return captured,body
 def test_health_explicitly_reports_unconfigured_integrations(self):
  with patch.dict(os.environ,{},clear=True): os.environ['APP_SECRET_KEY']='x'*48; r,b=self.request('/api/health')
  self.assertTrue(json.loads(b)['database']=='ok'); self.assertEqual(json.loads(b)['glpi'],'configuration_required')
 def test_ticket_endpoint_requires_login(self):
  r,b=self.request('/api/tickets'); self.assertTrue(r['status'].startswith('401'))
 def test_initial_setup_disabled_by_default(self):
  with patch.dict(os.environ,{'APP_SECRET_KEY':'x'*48},clear=True): r,b=self.request('/api/auth/setup','POST',{'username':'admin1','password':'A_secure_test_password!'}); self.assertTrue(r['status'].startswith('403'))
 def test_setup_then_me(self):
  with patch.dict(os.environ,{'APP_SECRET_KEY':'x'*48,'ALLOW_ADMIN_SETUP':'true'}):
   r,b=self.request('/api/auth/setup','POST',{'username':'testadmin','password':'A_secure_test_password!'}); self.assertTrue(r['status'].startswith('201')); cookie=r['headers']['Set-Cookie'].split(';',1)[0]
   r,b=self.request('/api/auth/me',cookie=cookie); self.assertEqual(json.loads(b)['user']['role'],'admin')
 def test_ticket_creation_validates_and_requires_linked_identity(self):
  with patch.dict(os.environ,{'APP_SECRET_KEY':'x'*48,'ALLOW_ADMIN_SETUP':'true'}):
   r,b=self.request('/api/auth/setup','POST',{'username':'testadmin','password':'A_secure_test_password!'}); cookie=r['headers']['Set-Cookie'].split(';',1)[0]
   r,b=self.request('/api/tickets','POST',{'name':'Test ticket','content':'Description valid'},cookie); self.assertTrue(r['status'].startswith('403'))
 def test_invalid_json_is_rejected(self):
  raw=b'{bad'; environ={'PATH_INFO':'/api/auth/login','REQUEST_METHOD':'POST','CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw),'HTTP_COOKIE':''}; captured={}
  r=b''.join(app(environ,lambda s,h:captured.update(status=s))); self.assertTrue(captured['status'].startswith('400'))
 def test_stock_entities_are_seven_and_unconfigured_by_default(self):
  with patch.dict(os.environ,{'APP_SECRET_KEY':'x'*48,'ALLOW_ADMIN_SETUP':'true'}):
   r,b=self.request('/api/auth/setup','POST',{'username':'testadmin','password':'A_secure_test_password!'}); cookie=r['headers']['Set-Cookie'].split(';',1)[0]
   r,b=self.request('/api/stocks/entities',cookie=cookie); entities=json.loads(b)['entities']
   self.assertEqual([e['code'] for e in entities],[f'STOCK-{i:02d}' for i in range(1,8)])
   self.assertTrue(all(not e['mapped'] for e in entities))
 def test_stock_endpoint_fails_closed_without_real_stock_adapter(self):
  with patch.dict(os.environ,{'APP_SECRET_KEY':'x'*48,'ALLOW_ADMIN_SETUP':'true'}):
   r,b=self.request('/api/auth/setup','POST',{'username':'testadmin','password':'A_secure_test_password!'}); cookie=r['headers']['Set-Cookie'].split(';',1)[0]
   r,b=self.request('/api/stocks','GET',cookie=cookie); self.assertTrue(r['status'].startswith('503')); self.assertIn('GLPI stock module',json.loads(b)['error'])
 def test_nonadmin_sees_only_assigned_stock_entity(self):
  with patch.dict(os.environ,{'APP_SECRET_KEY':'x'*48,'ALLOW_ADMIN_SETUP':'true'}):
   r,b=self.request('/api/auth/setup','POST',{'username':'testadmin','password':'A_secure_test_password!'}); admin=r['headers']['Set-Cookie'].split(';',1)[0]
   r,b=self.request('/api/admin/users','POST',{'username':'store02','password':'Store_account_password!','role':'user','stock_entity_code':'STOCK-02'},admin); self.assertTrue(r['status'].startswith('201'))
   r,b=self.request('/api/auth/login','POST',{'username':'store02','password':'Store_account_password!'}); local=r['headers']['Set-Cookie'].split(';',1)[0]
   r,b=self.request('/api/stocks/entities',cookie=local); entities=json.loads(b)['entities']; self.assertEqual([x['code'] for x in entities],['STOCK-02'])
   r,b=self.request('/api/admin/entities','GET',cookie=local); self.assertTrue(r['status'].startswith('403'))
 def test_stock_entity_map_is_admin_only_and_validated(self):
  with patch.dict(os.environ,{'APP_SECRET_KEY':'x'*48,'ALLOW_ADMIN_SETUP':'true'}):
   r,b=self.request('/api/auth/setup','POST',{'username':'testadmin','password':'A_secure_test_password!'}); cookie=r['headers']['Set-Cookie'].split(';',1)[0]
   r,b=self.request('/api/admin/entities','POST',{'code':'STOCK-01','name':'Site de test','glpi_entity_id':17},cookie); self.assertTrue(r['status'].startswith('200'))
   r,b=self.request('/api/admin/entities','POST',{'code':'STOCK-08','name':'Invalid','glpi_entity_id':99},cookie); self.assertTrue(r['status'].startswith('400'))
   r,b=self.request('/api/admin/entities','GET',cookie=cookie); self.assertEqual(json.loads(b)['entities'][0]['glpi_entity_id'],17)
 def test_glpi_session_flow_uses_and_closes_session_token(self):
  from app import glpi_request
  class FakeResponse:
   def __init__(self,data): self.data=json.dumps(data).encode()
   def __enter__(self): return self
   def __exit__(self,*a): pass
   def read(self): return self.data
  replies=[FakeResponse({'session_token':'session-123'}),FakeResponse({'totalcount':0,'data':[]}),FakeResponse({'ok':True})]
  with patch.dict(os.environ,{'GLPI_BASE_URL':'https://glpi.example','GLPI_APP_TOKEN':'app','GLPI_USER_TOKEN':'user'}), patch('app.urllib.request.urlopen',side_effect=replies) as mocked:
   result=glpi_request('GET','/search/Ticket?range=0-49')
  self.assertEqual(result['totalcount'],0); self.assertEqual(mocked.call_count,3)
  self.assertIn('session-token', {k.lower() for k in mocked.call_args_list[1].args[0].headers})
  self.assertEqual(mocked.call_args_list[2].args[0].full_url,'https://glpi.example/apirest.php/killSession')
if __name__=='__main__': unittest.main()
