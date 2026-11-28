# Portail ITSM + stocks FSS — GLPI, agents IA et assistant connecté

Application web locale en français (Python 3, bibliothèque standard uniquement + SQLite) qui relie **GLPI** à un portail simple pour la Faculté des Sciences de Sfax :
tickets de support, gestion de stock par entité, agents IA qui s'entraident, et un assistant IA relié aux données du portail.
**Les données métier restent dans GLPI** (tickets, entités, consommables). SQLite ne garde que les comptes, les liens d'entités, les messages entre agents, les transferts, les journaux et les réglages.

## Fonctionnalités

| Domaine | Ce que l'application fait |
|---|---|
| **Tickets** | Liste, création **(type, urgence, catégorie GLPI, lieu)**, **détail avec suivi (commentaires)**, états GLPI (Nouveau, En cours, Planifié, En attente/bloqué, Résolu, Clos) changés par l'administrateur avec commentaire et **historique** (qui/quand/pourquoi). « Résolu » crée une solution GLPI. |
| **Stocks** | 7 entités enfants (STOCK-01 à 07) créées/liées dans GLPI. Quantités lues dans les **Consommables GLPI** : création d'article, entrée, sortie, modification, suppression (corbeille GLPI), alertes de seuil. |
| **Tableau de bord** | Accueil : **« À traiter »** (tickets à prendre en charge, bloqués, transferts, articles critiques), tickets par état, activité récente. Stocks : KPI, articles à réapprovisionner, santé par stock, transferts en attente. |
| **Prévisions de stock** | Estimation des **jours restants** et de la **quantité à commander** à partir des sorties des 30 derniers jours (fenêtre minimale 7 jours, indicative), consommation par stock, **liste de commande exportable en CSV**. |
| **Journal et exports** | Journal des mouvements de stock (qui, quoi, quand), exports **CSV** (stock et journal, compatibles Excel, protégés contre l'injection de formules), journal d'activité administrateur. |
| **Agents IA** | Un agent par stock + un agent administrateur : ils lisent GLPI, s'écrivent, proposent des transferts. **Un humain approuve** (sauf petits transferts si l'option est activée, avec garde-fous). « Ronde » manuelle ou planifiée. |
| **Assistant IA** | Connecté au portail : lit vos tickets et votre stock (selon vos droits), aide au dépannage, **prépare** un ticket ou un changement d'état que vous confirmez d'un clic. Il ne modifie jamais rien seul. |
| **Comptes** | Rôles admin / technicien / utilisateur, rattachement à un stock et à un utilisateur GLPI, changement de mot de passe (« Mon compte »), gestion des comptes par l'administrateur. |
| **Exploitation** | Sauvegarde SQLite manuelle et **automatique toutes les 24 h** (14 copies), tests unitaires, `selftest.py` de bout en bout, `check_glpi.py` et `test_ai.py` de diagnostic. |

## Architecture

```
Navigateur ──HTTP──> app.py (WSGI, threads) ──REST v1──> GLPI (apirest.php)
  static/*.js,css        │   └──Chat Completions──> fournisseur IA (Groq, Ollama…)
                         └── SQLite (data/app.sqlite3): comptes, liens d'entités, journaux, transferts, réglages
```
Une seule application, aucune dépendance externe. Le serveur lit `.env` au démarrage. Un thread de fond exécute la ronde planifiée et la sauvegarde quotidienne.

## Installation (Windows)

Prérequis : Python 3.10+ et un GLPI avec l'API REST activée.

```cmd
cd C:\wamp64\www\fss-glpi-project
copy .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
notepad .env
python app.py
```
Collez le secret généré dans `APP_SECRET_KEY` puis ouvrez http://127.0.0.1:8000.

### Configuration `.env`

| Variable | Rôle |
|---|---|
| `APP_SECRET_KEY` | **Obligatoire**, 32 caractères minimum (signature des cookies). Le changer déconnecte tout le monde. |
| `APP_DB_PATH`, `HOST`, `PORT` | Base SQLite (défaut `data/app.sqlite3`), adresse (défaut `127.0.0.1`) et port (`8000`). |
| `ALLOW_ADMIN_SETUP` | `true` **uniquement** pour créer le premier administrateur, puis remettre `false`. |
| `GLPI_BASE_URL` | URL de GLPI **sans** `/apirest.php` (ex. `http://glpi.local`). |
| `GLPI_APP_TOKEN`, `GLPI_USER_TOKEN` | Jetons de l'API GLPI (utilisateur au profil Super-Admin pour créer les entités). |
| `GLPI_ALLOW_HTTP` | `true` pour autoriser `http://` vers un serveur interne (garder HTTPS en production). |
| `GLPI_VERIFY_TLS` | `false` pour un certificat auto-signé (test seulement). |
| `GLPI_PARENT_ENTITY_ID` | Entité parente sous laquelle créer les 7 stocks (`0` = racine). |
| `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL` | Fournisseur IA compatible Chat Completions **avec appel d'outils** (ex. Groq `https://api.groq.com/openai/v1`, Ollama `http://localhost:11434/v1`). Les 3 sont requis. |
| `APP_ENV` | `production` : cookies `Secure` + en-tête HSTS (nécessite HTTPS). |
| `TRUST_PROXY` | `true` derrière un reverse proxy local (Apache) : IP réelle des clients et contrôle d'origine corrects. |
| `LOGIN_IP_LIMIT` | Tentatives de connexion par minute et par IP (défaut 30) ; 6 par minute et par compte en plus. |

### Configuration GLPI
1. *Configuration > Générale > API* : activer l'API REST et la connexion par jeton externe.
2. Dans *Clients de l'API* : régénérer l'**App-Token** et autoriser l'IP du serveur.
3. Dans le profil de l'utilisateur d'intégration : *Clé d'accès distante > API token*.
4. Vérifier : `python check_glpi.py` (chaque ligne doit être `[OK]`).

### Premier lancement
1. `ALLOW_ADMIN_SETUP=true`, lancer l'application, créer l'administrateur sur l'écran d'initialisation, puis remettre `false` et relancer.
2. *Administration > Comptes* : lier votre compte à votre **ID utilisateur GLPI** (ex. 2). Sans lui : pas de sorties de stock ni d'approbation.
3. *Administration > « Créer / synchroniser les 7 entités dans GLPI »*.
4. Créer un compte par magasinier (rôle Magasinier, stock, ID GLPI), éventuellement « Créer des articles de démonstration ».

## Rôles et droits

| | Administrateur | Magasinier / utilisateur |
|---|---|---|
| Tickets | tous ; change les états | les siens ; peut commenter |
| Stocks, articles, journal | tous les stocks | son stock uniquement |
| Agents | tous + agent ADMIN + ronde | son agent uniquement |
| Transferts | approuve / refuse | consulte ceux de son stock |
| Comptes, réglages, sauvegardes, journal d'activité | oui | non |

## Tests

```cmd
python -m unittest discover -s tests     :: 39 tests (GLPI et IA simulés, aucun accès réseau)
python app.py                            :: dans une fenêtre
python selftest.py                       :: dans une autre : test de bout en bout contre votre GLPI et votre IA
python check_glpi.py                     :: diagnostic de la connexion GLPI
python test_ai.py                        :: diagnostic du fournisseur IA
```
`selftest.py` demande confirmation avant chaque étape qui écrit dans GLPI et nettoie ses données de test (article, compte). Le ticket de test reste « Résolu » (GLPI ne permet pas de le supprimer par l'API).

## Sauvegarde et restauration
- *Administration > Sauvegardes* : « Sauvegarder maintenant ». Copies dans `data/backups/` (permissions restreintes), automatiques toutes les 24 h, 14 conservées.
- Restaurer : arrêter l'application, remplacer `data/app.sqlite3` par une copie, relancer. Sauvegardez aussi `.env`.
- La base contient les hachages des mots de passe : protégez le dossier `data/`.

## Sécurité
Mots de passe PBKDF2-SHA256 (310 000 itérations), cookie signé `HttpOnly` + `SameSite=Strict` (+ `Secure` en production), contrôle d'origine, limites de débit par IP **et par compte**, en-têtes de sécurité (CSP, `nosniff`, `X-Frame-Options`, HSTS en production) sur la page, les ressources statiques et l'API, validation stricte des entrées, journal d'audit. Les agents IA ne modifient jamais le stock seuls : ils lisent, écrivent et proposent ; les contenus venant de GLPI ou des messages sont traités comme non fiables.

**Avant d'ouvrir à d'autres utilisateurs, suivre `docs/Deploiement_FSS.md`** : sortir le projet du dossier `www` d'Apache (sinon `.env` et la base peuvent être téléchargeables), nouveaux jetons, reverse proxy **HTTPS**, service Windows, sauvegarde hors serveur testée, check-list de mise en service.

## Dépannage

| Message | Cause probable |
|---|---|
| `Set APP_SECRET_KEY…` | `.env` introuvable ou lancé depuis un autre dossier. |
| `GLPI is unreachable` / `resource not found` | Mauvaise `GLPI_BASE_URL` (ni `/apirest.php`, ni sous-dossier faux), nom non résolu. Lancer `check_glpi.py`. |
| `GLPI authentication failed` | App-Token / User-Token faux, API désactivée ou IP non autorisée. |
| `AI provider error: URL or model name not found` | Nom de modèle IA obsolète : le remplacer dans `AI_MODEL`. |
| `Rate limit reached` | Quota gratuit du fournisseur IA : attendre ou espacer les rondes. |
| Le modèle n'utilise pas les outils | Essayer un modèle plus grand (ex. `openai/gpt-oss-120b`). |
| `Your account needs a GLPI user id` | Lier le compte à un ID GLPI (Administration > Comptes). |
| « Résolu » ou « Clos » refusé | Règle de workflow GLPI : le message de GLPI s'affiche, passer par « Résolu » avant « Clos ». |

## Limites connues
- La sortie de stock et le transfert enregistrent les unités comme « données à » un utilisateur GLPI (mécanisme natif des consommables).
- Les quantités sont recalculées depuis GLPI à chaque lecture (2 000 lignes max.) : adapté à un pilote, à optimiser pour de gros volumes.
- Pas de notifications par e-mail depuis le portail (utiliser les notifications GLPI).
- Pas de mode sombre ni de multilingue.

Les documents du dossier `docs/` décrivent la conception initiale ; ce README fait foi pour l'état actuel.
