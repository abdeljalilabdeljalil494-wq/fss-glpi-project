# Guide de mise en service à la FSS (Windows + WAMP/Apache)

Objectif : faire tourner le portail pour de vrais utilisateurs, en **HTTPS**, qui redémarre tout seul, sauvegardé, et sans exposer `.env` ni la base.

```
Utilisateurs ──HTTPS 443──> Apache (WAMP, reverse proxy) ──HTTP──> 127.0.0.1:8000 (service Python "FSSPortail")
                                                                       ├── GLPI (même serveur, http://glpi.local)
                                                                       ├── SQLite  C:\fss-portail\data\
                                                                       └── Fournisseur IA (Groq…) via Internet
```

## 0. Décisions à valider avec la DSI avant de commencer
1. **Nom DNS** du portail (ex. `portail.fss.tn`) : un enregistrement DNS interne vers l'IP du serveur (en test, le fichier `hosts` de chaque poste suffit).
2. **Certificat HTTPS** : celui de l'université si elle en fournit un ; sinon auto-signé (étape 4) à installer comme « autorité de confiance » sur les postes.
3. **Qui administre** le serveur, les sauvegardes et les comptes (au moins deux personnes).
4. **Confidentialité de l'IA** (étape 10) : les titres et descriptions de tickets lus par les agents et l'assistant partent chez le fournisseur IA. Décider si c'est acceptable ou si l'on utilise un modèle local (Ollama).

## 1. ⚠ Sortir le projet du dossier `www` d'Apache
Le dossier `C:\wamp64\www\` est servi par Apache. La règle d'origine d'Apache ne protège que les fichiers `.ht*` : **`.env` (jetons) et `data\app.sqlite3` (comptes) peuvent être téléchargeables** dès que le serveur est joignable sur le réseau.

Test (10 secondes) : ouvrez `http://localhost/fss-glpi-project/.env`. Si le contenu s'affiche, c'est exposé. Quel que soit le résultat, faites ceci :

```cmd
:: arrêter l'application, puis :
robocopy C:\wamp64\www\fss-glpi-project C:\fss-portail /E /XD .git __pycache__ logs
mkdir C:\fss-portail\logs
```
Travaillez désormais dans `C:\fss-portail` (le `.env` et le dossier `data\` sont copiés avec). Supprimez ensuite l'ancien dossier de `www`. Pour un dépôt Git : `git clone` directement dans `C:\fss-portail`.

Restreindre l'accès aux secrets (administrateur seulement) :
```cmd
icacls C:\fss-portail\.env /inheritance:r /grant SYSTEM:F /grant Administrators:F
icacls C:\fss-portail\data /inheritance:r /grant SYSTEM:(OI)(CI)F /grant Administrators:(OI)(CI)F
```

## 2. Configuration de production (`C:\fss-portail\.env`)
```ini
APP_ENV=production              # cookies "Secure" + en-tête HSTS (exige HTTPS)
APP_SECRET_KEY=<64 caractères aléatoires : python -c "import secrets; print(secrets.token_urlsafe(48))">
HOST=127.0.0.1                  # ne jamais écouter sur le réseau : seul Apache parle à l'application
PORT=8000
TRUST_PROXY=true                # lit l'IP réelle et l'hôte transmis par Apache (sinon tout le monde a l'IP 127.0.0.1)
ALLOW_ADMIN_SETUP=false         # true seulement pour créer le 1er administrateur
LOGIN_IP_LIMIT=30               # tentatives de connexion par minute et par IP (postes derrière un même NAT)

GLPI_BASE_URL=http://glpi.local
GLPI_ALLOW_HTTP=true            # GLPI est sur la même machine : trafic local uniquement
GLPI_APP_TOKEN=...              # NOUVEAUX jetons (étape 6)
GLPI_USER_TOKEN=...
GLPI_PARENT_ENTITY_ID=0

AI_BASE_URL=https://api.groq.com/openai/v1
AI_API_KEY=...                  # NOUVELLE clé dédiée à la production
AI_MODEL=openai/gpt-oss-20b
```

## 3. Service Windows (démarrage automatique et redémarrage après plantage)
Python doit être installé **pour tous les utilisateurs** (python.org, option « Install for all users »), pas dans `AppData`. Vérifiez : `where python`.

Avec **NSSM** (nssm.cc) :
```cmd
mkdir C:\fss-portail\logs
nssm install FSSPortail "C:\Program Files\Python312\python.exe" app.py
nssm set FSSPortail AppDirectory C:\fss-portail
nssm set FSSPortail AppStdout C:\fss-portail\logs\app.log
nssm set FSSPortail AppStderr C:\fss-portail\logs\app.log
nssm set FSSPortail AppRotateFiles 1
nssm set FSSPortail AppRotateBytes 5000000
nssm set FSSPortail Start SERVICE_AUTO_START
nssm start FSSPortail
```
Sans NSSM (planificateur de tâches) :
```cmd
schtasks /create /tn "FSS Portail" /sc onstart /ru SYSTEM /rl HIGHEST /tr "cmd /c cd /d C:\fss-portail && python app.py >> logs\app.log 2>&1"
```
Test : `curl http://127.0.0.1:8000/api/health` doit répondre `"application":"ok"`. Redémarrez le serveur une fois pour vérifier que le service remonte seul.

## 4. Apache en reverse proxy HTTPS
1. Dans WAMP : *Apache > Modules Apache* : cocher `proxy_module`, `proxy_http_module`, `ssl_module`, `headers_module`, `socache_shmcb_module`.
2. Certificat auto-signé (ignorez cette étape si la DSI fournit un certificat) :
```cmd
mkdir C:\wamp64\certs
cd C:\wamp64\bin\apache\apache2.4.62\bin
openssl req -x509 -nodes -newkey rsa:2048 -days 825 -keyout C:\wamp64\certs\portail.key -out C:\wamp64\certs\portail.crt -subj "/CN=portail.fss.local" -addext "subjectAltName=DNS:portail.fss.local" -config C:\wamp64\bin\apache\apache2.4.62\conf\openssl.cnf
```
(le dossier `apache2.4.62` dépend de votre version.) Importez `portail.crt` dans « Autorités de certification racines de confiance » sur les postes clients, sinon le navigateur affichera un avertissement.
3. Ajoutez à `httpd-vhosts.conf` :
```apache
<VirtualHost *:80>
    ServerName portail.fss.local
    Redirect permanent / https://portail.fss.local/
</VirtualHost>

<VirtualHost *:443>
    ServerName portail.fss.local
    SSLEngine on
    SSLCertificateFile    "C:/wamp64/certs/portail.crt"
    SSLCertificateKeyFile "C:/wamp64/certs/portail.key"

    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    ProxyTimeout 300          # la « ronde des agents » peut durer plus d'une minute
    ProxyPass        / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
</VirtualHost>
```
4. Redémarrez Apache, ajoutez `portail.fss.local` au fichier `hosts` (ou au DNS) et ouvrez `https://portail.fss.local`.

Pare-feu : n'ouvrir que le 443 (et le 80 pour la redirection). Le port 8000 reste fermé de l'extérieur.
```cmd
netsh advfirewall firewall add rule name="FSS Portail HTTPS" dir=in action=allow protocol=TCP localport=443
```

## 5. Sauvegardes
L'application sauvegarde sa base toutes les 24 h dans `C:\fss-portail\data\backups` (14 copies). **Une sauvegarde sur le même disque ne protège pas d'une panne du disque** : copiez-la ailleurs chaque jour avec `scripts\backup_offsite.bat` (modifiez la destination), planifié :
```cmd
schtasks /create /tn "FSS Sauvegarde" /sc daily /st 02:00 /ru SYSTEM /tr "C:\fss-portail\scripts\backup_offsite.bat"
```
Sauvegardez aussi `.env` (coffre de mots de passe de la DSI). **Testez une restauration** une fois avant la mise en service.

## 6. GLPI : utilisateur d'intégration et jetons
- Créez un utilisateur GLPI dédié (ex. `api-portail`), pas votre compte personnel.
- Régénérez l'**App-Token** et l'**API token** ; dans le client d'API, limitez les IP autorisées à `127.0.0.1` / l'IP du serveur.
- Le profil **Super-Admin** n'est nécessaire que pour *créer* les 7 entités. Une fois les entités créées et liées, passez à un profil limité aux tickets, aux consommables et à la lecture des entités, puis relancez `python selftest.py` pour vérifier.

## 7. Premier démarrage en production
1. `ALLOW_ADMIN_SETUP=true` → redémarrer le service → créer l'administrateur → remettre `false` → redémarrer.
2. *Administration > Comptes* : renseigner votre ID utilisateur GLPI. *« Créer / synchroniser les 7 entités »*.
3. Créer un compte par magasinier (stock + ID GLPI). **N'utilisez pas le « jeu d'essai »** en production.
4. Changer son mot de passe via « Mon compte » (clic sur la pastille de rôle).

## 8. Recette avant ouverture
- `python -m unittest discover -s tests` (31 tests) puis `python selftest.py` sur le serveur : écrit un article et un ticket de test, nettoie le reste.
- Vérifier depuis un autre poste : HTTPS sans avertissement, connexion, création de ticket, un magasinier ne voit que son stock, une sauvegarde manuelle.
- Débrancher Internet 1 minute : le portail et GLPI restent utilisables, seules les fonctions IA signalent une erreur.

## 9. Déploiement progressif
1. **Pilote** : 1 à 2 stocks et 3 à 5 utilisateurs pendant 2 semaines. Relever les blocages.
2. **Formation** de 30 minutes : créer/suivre un ticket, commentaires, entrées/sorties, lire une alerte, quand demander à l'agent.
3. **Généralisation** aux 7 stocks. Garder une personne référente et un canal de support.

## 10. Exploitation
| Sujet | Pratique |
|---|---|
| Mise à jour | Sauvegarde manuelle → `git pull` (ou copie des fichiers) → `nssm restart FSSPortail` → `python selftest.py`. Les migrations de base sont additives et automatiques. Retour arrière : restaurer le code précédent (et la sauvegarde si besoin). |
| Supervision | `https://portail.fss.local/api/health` (application, base, GLPI, IA). Logs dans `logs\app.log` (rotation 5 Mo). |
| Comptes | Départ d'un agent : supprimer son compte (Administration > Comptes). Revue des comptes chaque trimestre. |
| Secrets | Régénérer les jetons GLPI et la clé IA à chaque départ d'un administrateur, et au minimum chaque année. |
| Quota IA | Offre gratuite limitée : espacer la ronde planifiée (≥ 60 min) ; en cas de `Rate limit`, patienter. |
| Journal | *Administration > Journal d'activité* et *Journal des mouvements* (exports CSV). |

### Confidentialité et IA
Le fournisseur IA reçoit les messages saisis, ainsi que les résultats des outils (titres/descriptions de tickets, quantités de stock). Pour limiter l'exposition : informer les utilisateurs de ne pas saisir de données personnelles sensibles dans l'assistant, choisir un fournisseur dont les conditions conviennent à l'établissement, ou héberger un modèle local (Ollama : `AI_BASE_URL=http://localhost:11434/v1`). Les agents ne modifient jamais le stock seuls ; les petits transferts automatiques sont désactivés par défaut.

## 11. Check-list de mise en service
- [ ] Projet déplacé hors de `www` ; `.env` et `data\` inaccessibles par HTTP et restreints par `icacls`
- [ ] Nouveaux jetons GLPI et nouvelle clé IA ; ancien contenu des `.env` de test détruit
- [ ] `APP_ENV=production`, `TRUST_PROXY=true`, `HOST=127.0.0.1`, `ALLOW_ADMIN_SETUP=false`
- [ ] HTTPS valide sur le nom DNS définitif ; port 8000 fermé au pare-feu
- [ ] Service qui redémarre seul (test de redémarrage du serveur effectué)
- [ ] Sauvegarde automatique + copie hors serveur planifiée ; **restauration testée**
- [ ] Tests unitaires et `selftest.py` au vert sur le serveur
- [ ] Comptes créés (un par personne), mots de passe changés, IDs GLPI renseignés
- [ ] Décision écrite sur le fournisseur IA et la confidentialité
- [ ] Pilote validé, formation faite, référent désigné

## 12. Dépannage en production
| Symptôme | Cause et solution |
|---|---|
| `403 Cross-origin request rejected` à chaque action | `TRUST_PROXY` absent, ou Apache sans `ProxyPreserveHost On`. |
| `429 Too many requests` à la connexion pour tout le monde | `TRUST_PROXY=true` manquant (tous les postes partagent l'IP 127.0.0.1). |
| Connexion impossible, cookie refusé | `APP_ENV=production` sans HTTPS : le cookie « Secure » ne passe pas en HTTP. |
| `502 Bad Gateway` | Le service est arrêté : `nssm status FSSPortail`, lire `logs\app.log`. |
| La ronde échoue après 1 minute | `ProxyTimeout 300` absent dans Apache. |
| `GLPI is unreachable` depuis le service | Le compte du service ne résout pas `glpi.local` : mettre le nom dans le fichier `hosts` du serveur. |
