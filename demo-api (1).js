/* MODE DÉMO — remplace le backend Python/GLPI par des données fictives en mémoire.
   Chargé AVANT app.js : intercepte fetch('/api/...'). Aucune donnée réelle. */
(()=>{
const now=()=>new Date().toISOString().slice(0,16);
const ago=d=>new Date(Date.now()-d*864e5).toISOString().slice(0,16);
const names=['Laboratoire informatique','Salles de TP','Administration','Bibliothèque','Département Physique','Département Chimie','Atelier réseau'];
const ents=names.map((n,i)=>({code:'STOCK-0'+(i+1),name:n,glpi_entity_id:10+i}));
let nid=100;
const it=(c,name,q,t)=>({id:nid++,code:c,name,quantity:q,threshold:t});
let items=[
it('STOCK-01','Câble RJ45 Cat6 (2 m)',34,10),it('STOCK-01','Souris USB',4,8),it('STOCK-01','Clavier AZERTY',12,5),
it('STOCK-02','Cartouche toner HP 85A',2,4),it('STOCK-02','Câble HDMI',15,6),it('STOCK-02','Pile AA (lot de 4)',9,6),
it('STOCK-03','Ramette papier A4',40,20),it('STOCK-03','Cartouche toner Brother TN',3,3),
it('STOCK-04','Clé USB 32 Go',18,6),it('STOCK-04','Disque dur externe 1 To',1,3),
it('STOCK-05','Multiprise 5 prises',11,4),it('STOCK-06','Adaptateur USB-C',7,5),it('STOCK-07','Connecteur RJ45 (boîte de 100)',2,3),it('STOCK-07','Switch 8 ports',5,2)];
let tickets=[
[501,'Imprimante du labo 1 bloquée',2,4,ago(1)],[502,'Wi-Fi indisponible en salle B12',1,5,ago(3)],
[503,'Installation de Python sur 20 postes',3,3,ago(6)],[504,'Demande de compte GLPI pour un enseignant',4,2,ago(9)],
[505,'Vidéoprojecteur amphi 2 ne s’allume pas',5,4,ago(14)],[506,'Mot de passe messagerie oublié',6,2,ago(20)]
].map(([id,name,s,p,d])=>({id,name,status:s,priority:p,date:d,'1':name,'2':id,'12':s,'3':p,'15':d}));
const SL={1:'Nouveau',2:'En cours',3:'Planifié',4:'En attente (bloqué)',5:'Résolu',6:'Clos'};
let fu={501:[{author:'Technicien FSS',date:ago(1),content:'Pris en charge. Je passe au labo 1 cet après-midi.'}],505:[{author:'Technicien FSS',date:ago(13),content:'Lampe remplacée.'}]};
let transfers=[{id:1,from_code:'STOCK-03',to_code:'STOCK-02',item_name:'Cartouche toner HP 85A',qty:2,status:'pending',note:'Proposé par l’agent STOCK-02'}];
let msgs=[{from_code:'STOCK-02',to_code:'ADMIN',body:'Toner HP 85A sous le seuil (2/4). Je propose un transfert depuis STOCK-03.',created_at:ago(0)},
{from_code:'STOCK-04',to_code:'ADMIN',body:'Disque dur externe : 1 restant pour un seuil de 3.',created_at:ago(0)}];
let moves=[{kind:'exit',created_at:ago(1),username:'demo',stock_code:'STOCK-01',item_name:'Souris USB',qty:3,note:'Remise à un enseignant'},
{kind:'entry',created_at:ago(4),username:'demo',stock_code:'STOCK-03',item_name:'Ramette papier A4',qty:20,note:'Réception commande'},
{kind:'exit',created_at:ago(6),username:'demo',stock_code:'STOCK-02',item_name:'Cartouche toner HP 85A',qty:2,note:''}];
let events=[{created_at:ago(0),username:'demo',event:'login'},{created_at:ago(1),username:'demo',event:'backup'}];
let users=[{id:1,username:'demo',role:'admin',stock_entity_code:null,glpi_user_id:2},{id:2,username:'magasinier01',role:'user',stock_entity_code:'STOCK-01',glpi_user_id:7},{id:3,username:'tech01',role:'technician',stock_entity_code:null,glpi_user_id:5}];
const low=i=>i.threshold>0&&i.quantity<=i.threshold;
const pub=i=>({id:i.id,name:i.name,quantity:i.quantity,threshold:i.threshold,low:low(i)});
const list=c=>items.filter(i=>i.code===c).map(pub);
const log=(kind,i,qty,note='')=>moves.unshift({kind,created_at:now(),username:'demo',stock_code:i.code,item_name:i.name,qty,note});
function overview(){
 const stocks=ents.map(e=>{const l=items.filter(i=>i.code===e.code),lw=l.filter(low);
  return{code:e.code,name:e.name,linked:true,verified:1,glpi_name:'FSS > '+e.code,articles:l.length,units:l.reduce((a,i)=>a+i.quantity,0),ok_articles:l.length-lw.length,
  low:lw.map(i=>({name:i.name,quantity:i.quantity,threshold:i.threshold})),
  transfers_in:transfers.filter(t=>t.status==='pending'&&t.to_code===e.code).length,transfers_out:transfers.filter(t=>t.status==='pending'&&t.from_code===e.code).length}});
 return{stocks,totals:{linked:7,stocks:7,articles:items.length,units:items.reduce((a,i)=>a+i.quantity,0),low_items:items.filter(low).length,pending_transfers:transfers.filter(t=>t.status==='pending').length}}}
function insights(){
 const rows=items.map(i=>{const c=Math.max(0,Math.round(i.threshold*2.2)),d=c?Math.round(i.quantity/c*30):null;
  const pr=i.quantity===0||(d!==null&&d<=7)?'critical':(low(i)||(d!==null&&d<=14))?'soon':'ok';
  return{stock:i.code,article:i.name,quantity:i.quantity,threshold:i.threshold,consumption_30d:c,days_left:d,reliable:c>=5,suggested_order:pr==='ok'?0:Math.max(0,i.threshold*3-i.quantity),priority:pr}}).sort((a,b)=>'critical soon ok'.indexOf(a.priority)-'critical soon ok'.indexOf(b.priority));
 const ex={};rows.forEach(r=>ex[r.stock]=(ex[r.stock]||0)+r.consumption_30d);
 return{rows,summary:{critical:rows.filter(r=>r.priority==='critical').length,soon:rows.filter(r=>r.priority==='soon').length,exits_30d:ex},method:'Démo : estimation à partir des sorties fictives des 30 derniers jours (fenêtre minimale 7 jours, indicative).'}}
function answer(m){m=m.toLowerCase();
 if(/ticket/.test(m))return{answer:'Vous avez '+tickets.length+' tickets dont '+tickets.filter(t=>t.status<5).length+' ouverts. Le plus récent : « '+tickets[0].name+' » ('+SL[tickets[0].status]+').',tools_used:['list_my_tickets']};
 if(/stock|toner|article|seuil/.test(m)){const o=overview();return{answer:o.totals.low_items+' article(s) sont sous leur seuil : '+items.filter(low).map(i=>i.name+' ('+i.quantity+'/'+i.threshold+')').join(', ')+'. Un transfert est en attente d’approbation.',tools_used:['get_stock','list_transfers']}}
 if(/wi-?fi|r[eé]seau|internet|pc|imprim/.test(m))return{answer:'Essayez d’abord : 1) redémarrer l’appareil, 2) vérifier le câble ou le Wi-Fi, 3) tester sur un autre poste. Si le problème persiste, je peux préparer un ticket pour vous.',ticket_draft:{title:'Problème de connexion / matériel',description:m,urgency:3},tools_used:[]};
 return{answer:'[Démo] Je suis l’assistant du portail FSS. Demandez-moi « où en sont mes tickets ? », « état du stock ? » ou décrivez une panne.',tools_used:[]}}
const J=(o,s=200)=>new Response(JSON.stringify(o),{status:s,headers:{'Content-Type':'application/json'}});
const E=(m,s=400)=>J({error:m},s);
const realFetch=window.fetch.bind(window);
window.fetch=async(url,o={})=>{
 const u=new URL(url,location.href);if(!u.pathname.includes('/api/'))return realFetch(url,o);
 const p=u.pathname.slice(u.pathname.indexOf('/api/')),q=u.searchParams,b=o.body?JSON.parse(o.body):{},M=(o.method||'GET').toUpperCase();
 await new Promise(r=>setTimeout(r,120));
 const code=b.code||q.get('code'),find=()=>items.find(i=>i.id===b.item_id&&i.code===code);
 switch(p){
 case'/api/auth/me':return J({user:{username:'demo',role:'admin',stock_entity_code:null,glpi_user_id:2}});
 case'/api/auth/logout':case'/api/auth/login':return J({ok:true});
 case'/api/auth/password':return E('Démo : changement de mot de passe désactivé.');
 case'/api/health':return J({application:'ok',database:'ok',glpi:'configured',ai:'configured'});
 case'/api/glpi/health':return J({status:'ok'});
 case'/api/tickets':if(M==='POST'){const id=Math.max(...tickets.map(t=>t.id))+1,n=b.name||b.title;tickets.unshift({id,name:n,status:1,priority:b.urgency||3,date:now(),'1':n,'2':id,'12':1,'3':b.urgency||3,'15':now()});fu[id]=[];return J({ok:true,id})}
  return J({data:{data:tickets}});
 case'/api/ticket/options':return J({categories:[{id:1,name:'Réseau'},{id:2,name:'Matériel'},{id:3,name:'Logiciel'},{id:4,name:'Comptes'}]});
 case'/api/ticket/detail':{const t=tickets.find(x=>x.id===+q.get('id'));if(!t)return E('Ticket introuvable',404);
  return J({ticket:{id:t.id,title:t.name,status:t.status,status_label:SL[t.status],date:t.date,priority:t.priority,description:'Description fictive du ticket (mode démo).'},followups:fu[t.id]||[],solutions:t.status>=5?[{date:t.date,content:'Problème résolu et vérifié avec l’utilisateur.'}]:[],can_comment:true})}
 case'/api/ticket/followup':(fu[b.ticket_id]=fu[b.ticket_id]||[]).push({author:'demo',date:now(),content:b.content});return J({ok:true});
 case'/api/admin/tickets/status':{const t=tickets.find(x=>x.id===+b.ticket_id);if(t){t.status=t['12']=+b.status;if(b.comment)(fu[t.id]=fu[t.id]||[]).push({author:'demo',date:now(),content:b.comment})}return J({ok:true})}
 case'/api/admin/tickets/history':return J({events:[{created_at:ago(2),username:'tech01',from_label:'Nouveau',to_label:'En cours',comment:'Pris en charge'}]});
 case'/api/stocks/entities':return J({entities:ents.map(e=>({...e,mapped:true}))});
 case'/api/stocks/overview':return J(overview());
 case'/api/stock/insights':return J(insights());
 case'/api/stock/items':if(M==='POST'){const i=it(code,b.name,b.quantity||0,b.threshold||0);items.push(i);log('create',i,i.quantity);}return J({items:list(code)});
 case'/api/stock/items/update':{const i=find();if(i){i.name=b.name;i.threshold=b.threshold;log('edit',i,0)}return J({items:list(code)})}
 case'/api/stock/items/delete':{const i=find();if(i){items=items.filter(x=>x!==i);log('delete',i,0)}return J({items:list(code)})}
 case'/api/stock/entry':{const i=find();if(i){i.quantity+=b.quantity;log('entry',i,b.quantity)}return J({items:list(code)})}
 case'/api/stock/exit':{const i=find();if(i){if(i.quantity<b.quantity)return E('Quantité insuffisante en stock.');i.quantity-=b.quantity;log('exit',i,b.quantity)}return J({items:list(code)})}
 case'/api/stock/movements':return J({movements:moves.filter(m=>!code||m.stock_code===code).slice(0,+q.get('limit')||30)});
 case'/api/transfers':return J({transfers});
 case'/api/transfers/decide':{const t=transfers.find(x=>x.id===b.id);if(t){t.status=b.decision==='approve'?'approved':'rejected';if(t.status==='approved'){const s=items.find(i=>i.code===t.from_code&&i.name===t.item_name),d=items.find(i=>i.code===t.to_code&&i.name===t.item_name);if(s)s.quantity-=t.qty;if(d)d.quantity+=t.qty}}return J({ok:true})}
 case'/api/agents/inbox':return J({messages:msgs});
 case'/api/agents/chat':return J({answer:'['+b.agent+'] '+answer(b.message).answer});
 case'/api/agents/round':return J({report:['STOCK-02 : toner HP 85A sous le seuil → transfert proposé depuis STOCK-03.','STOCK-04 : disque dur externe sous le seuil → message envoyé à ADMIN.','Démo : aucune action réelle n’est effectuée.']});
 case'/api/assistant/chat':return J(answer(b.message));
 case'/api/admin/entities':return J({entities:ents.map(e=>({...e,verified:1,glpi_name:'FSS > '+e.code}))});
 case'/api/admin/entities/sync':return J({report:{created:[],linked:[],already_ok:ents.map(e=>e.code)}});
 case'/api/admin/entities/verify':return J({glpi_entities_seen:8});
 case'/api/admin/users':if(M==='POST')users.push({id:users.length+1,username:b.username,role:b.role,stock_entity_code:b.stock_entity_code||null,glpi_user_id:b.glpi_user_id||null});return J({users});
 case'/api/admin/users/update':{const u2=users.find(x=>x.id===b.id);if(u2)Object.assign(u2,{role:b.role,stock_entity_code:b.stock_entity_code,glpi_user_id:b.glpi_user_id});return J({ok:true})}
 case'/api/admin/users/delete':users=users.filter(x=>x.id!==b.id);return J({ok:true});
 case'/api/admin/activity':return J({events});
 case'/api/admin/backups':return J({backups:[{file:'app-demo.sqlite3',date:ago(1),size:84000}]});
 case'/api/admin/backup':return J({file:'app-demo.sqlite3'});
 case'/api/admin/settings':return J({settings:{auto_max_qty:5,auto_glpi_user_id:2,round_interval_min:0,last_round_at:null,last_round_report:''},my_glpi_user_id:2});
 case'/api/admin/stock/demo':return J({created:0,skipped:0});
 }
 return E('Démo : cette fonction n’est pas disponible dans la version en ligne.',503)};
/* bannière */
document.addEventListener('DOMContentLoaded',()=>{
 const d=document.createElement('div');
 d.style.cssText='background:#1f2937;color:#fff;font:13px/1.4 system-ui,sans-serif;padding:8px 14px;text-align:center';
 d.innerHTML='🧪 <b>Démo en ligne</b> — données fictives, aucun serveur ni GLPI réel. Connecté en tant qu’administrateur « demo ». <a href="https://github.com/abdeljalilabdeljalil494-wq/fss-glpi-project" style="color:#93c5fd">Code source</a>';
 document.body.prepend(d)});
})();
