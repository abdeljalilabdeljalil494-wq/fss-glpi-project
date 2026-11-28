# Rapport technique — Assistant IA de gestion ITSM GLPI
## Faculté des Sciences de Sfax — Université de Sfax

**Version de travail — 31 octobre 2026**  
**État:** application pilote locale implémentée et tests unitaires exécutés; connexion réelle GLPI/IA non configurée ni vérifiée.

## 1. Présentation du projet
Ce projet fournit une interface web française pour faciliter le support informatique, la consultation et la création de tickets GLPI et l'assistance conversationnelle. Il répond au cahier des charges FSS fourni, qui décrit une gestion centralisée des actifs, des stocks, des interventions et des équipements de laboratoire. Le dépôt disponible lors de l'audit contenait des documents de spécification, modèles CSV et runbook, mais aucun code source, dépôt Git ou connexion GLPI. Une implémentation pilote a donc été créée dans le répertoire existant sans supprimer ces ressources.

## 2. Problématique et objectifs
Les registres manuels et l'historique de maintenance dispersé compliquent le suivi des équipements et les demandes. L'objectif logiciel est d'offrir un point d'accès sécurisé aux tickets et à des conseils d'assistance IA, tout en gardant GLPI comme référentiel des tickets et sans inventer de données. Le projet plus large de déploiement GLPI inclut également l'inventaire, le SNMP, les stocks, l'isolation départementale et les sauvegardes.

## 3. Analyse des besoins
Acteurs: utilisateur standard, technicien, administrateur. Fonctions livrées dans le pilote: authentification locale, tableau de bord et listes alimentés par API lorsque GLPI est disponible, création de demande, assistant connecté à un endpoint compatible chat-completions. Les chiffres sont affichés comme indisponibles si l'intégration manque. Les statistiques de tickets proviennent des données renvoyées par le GLPI configuré; elles ne sont pas simulées.

## 4. Cahier des charges fonctionnel
- Connexion/déconnexion et présentation du rôle.
- Contrôle d'accès côté serveur, comptes locaux et liaison facultative à l'identifiant utilisateur GLPI.
- Santé application/SQLite/état de configuration GLPI et IA.
- Listing, détail, et création de tickets par requête serveur-à-serveur GLPI.
- Interface de conversation IA via service côté serveur.
- Messages d'erreur et états vides explicites; français et mise en page responsive.

Non livrés à ce stade: modification/résolution/clôture et suivi/commentaires; recherche et pagination avancées; réservation; soldes/mouvements réels de stock (une structure d'entités et un écran de liaison sont présents, mais aucun mouvement n'est activé); outils IA qui consultent des tickets; SSO/MFA.

## 5. Exigences non fonctionnelles
Validation d'entrée, taille maximale de requête, mots de passe hachés avec PBKDF2-HMAC-SHA256 salé, cookie signé HttpOnly/SameSite Strict et durée de huit heures, HTTPS exigé pour intégrations distantes, limite en mémoire sur login/assistant, vérification Origin lorsque le navigateur l'envoie, messages d'erreur sans détail d'infrastructure, secrets serveur uniquement et absence de stockage des conversations. Ces contrôles réduisent certains risques mais ne constituent pas une homologation sécurité.

## 6. Architecture générale
Application Python 3 WSGI sans dépendances, interface HTML/CSS/JS statique, SQLite pour comptes locaux, services HTTP Python standard pour GLPI et IA. Le navigateur s'adresse uniquement au backend de même origine. GLPI demeure l'autorité sur les tickets. Les détails des composants et limites figurent dans `Architecture.md`.

## 7. Choix technologiques
Le workspace ne contenait aucun code d'application à réutiliser; Python 3.13.16 était disponible, tandis que PHP/Composer étaient absents dans l'environnement d'exécution. Une implémentation Python standard library évite l'installation de dépendances et rend les tests locaux immédiatement reproductibles. Cette décision facilite le pilote mais ne reprend pas l'environnement historique Windows/WAMP mentionné dans le cahier des charges. Pour une exploitation pérenne, l'équipe FSS doit valider le runtime et le serveur WSGI de production.

## 8. Conception des données
La base SQLite locale comprend les comptes (`users`: identifiant, nom utilisateur unique, hash, rôle, identifiant GLPI facultatif, date) et une table d'audit initiale. Aucun ticket GLPI n'est dupliqué localement et aucune conversation n'est conservée. Le schéma est initialisé idempotemment au démarrage; un outil de migration versionné n'est pas encore implémenté. Les secrets d'intégration restent dans l'environnement.

## 9. Intégration GLPI
Le client utilise l'API REST v1 `/apirest.php`, App-Token et User-Token, temps limite réseau, HTTPS requis hors localhost, réponses d'erreur assainies. Fonctions codées: test d'initialisation de session, recherche/listing, détail et création de ticket. La compatibilité des champs de recherche et du payload dépend de la version/configuration GLPI. Aucun serveur GLPI ni token réel n'a été fourni: aucune intégration réelle n'est revendiquée. La portée du jeton de service et l'équivalence des droits des identités locales doivent être testées; les contrôles d'accès actuels ne remplacent pas les permissions natives GLPI.

## 10. Assistant IA
Le backend accepte une question de 1 à 4000 caractères et envoie une requête à un endpoint compatible `/chat/completions`. La clé reste côté serveur; modèle, URL et délai sont configurables via l'environnement (le délai est fixe à 25 s dans le code courant). Une consigne demande une réponse en français par défaut, des conseils prudents, l'absence de divulgation de secrets et le traitement des contenus intégrés comme données non fiables. Aucun accès aux tickets via outil IA n'est implémenté; le modèle ne doit donc pas être présenté comme connaissant les données GLPI. Sans configuration, l'application renvoie un état indisponible et les tickets restent indépendants de l'IA.

## 11. Sécurité et accès
Les rôles locaux sont administrateur, technicien et utilisateur; les routes administratives sont protégées côté serveur. Le setup admin initial est désactivé par défaut et ne fonctionne qu'une fois après activation explicite. Les secrets ne sont pas retournés au navigateur. Limites: le cookie Secure n'est pas encore conditionné à un mode de production confirmé, absence de jeton CSRF synchronisé, limitation de requêtes mémoire (non distribuée), pas de MFA/SSO, journaux structurés incomplets, et mapping d'identité GLPI à valider. Le serveur WSGI embarqué est réservé au développement. Revue et tests de sécurité indépendants requis avant toute donnée réelle.

## 12. Réalisation technique
Fichiers principaux: `app.py` (WSGI, SQLite, services GLPI/IA), `static/index.html`, `static/style.css`, `static/app.js`, `.env.example`, tests sous `tests/`, contrat API et architecture sous `docs/`. Les pages permettent login, tableau de bord, listing et filtre textuel des tickets, formulaire de création, chat, affichage des sept codes de stock selon le périmètre utilisateur et liaison admin des IDs d'entités GLPI. Aucun solde ni mouvement de stock n'est retourné avant validation du module GLPI. L'interface indique clairement les intégrations non configurées.

## 13. Installation et déploiement
Python 3.10+ recommandé. Copier `.env.example`, exporter `APP_SECRET_KEY` (48 octets aléatoires minimum 32 caractères), choisir `APP_DB_PATH`, lancer `python app.py` en écoute locale. Pour initialiser le premier admin, définir temporairement `ALLOW_ADMIN_SETUP=true`, puis la retirer immédiatement. Production: ne pas utiliser `wsgiref`; placer sous WSGI maintenu et reverse proxy HTTPS, gérer les secrets via coffre, restreindre réseau et tester restauration. Les commandes détaillées sont dans README.

## 14. Protocole et résultats de test
Commande exécutée: `python -m unittest discover -s tests -v`. Résultat observé: 11 tests exécutés, 11 réussis, 0 échec, 0 ignoré. Couverture actuelle: santé sans intégrations, setup désactivé, rejet JSON mal formé, création d'admin et session, refus d'accès sans connexion, refus de créer un ticket sans identité GLPI liée, test mocké du cycle REST GLPI, catalogue de sept entités, refus fermé des opérations sans module de stock, contrôle/mapping d'entité admin. `python -m py_compile app.py tests/test_app.py` s'est aussi terminé avec code 0. Le serveur de développement a répondu HTTP 200 pour `/` et `/api/health` (application et SQLite ok; GLPI/IA explicitement non configurés). Ces contrôles ne valident pas une connexion réelle GLPI/IA.

## 15. Limites
Pas d'instance GLPI réelle, de fournisseur IA configuré, de données utilisateur, de permission réelle, de système de CI, de Git, de migration SQL versionnée, ni de test navigateur automatisé. Contrat API dépendant de la version GLPI. Les endpoints GLPI partagent actuellement le jeton de service configuré; cloisonnement par département non prouvé. Pas de modération provider, audit de sécurité indépendant, restauration testée, haute disponibilité ou déploiement faculty.

## 16. Architecture de stock à sept entités (schémas complémentaires)
Les diagrammes ajoutés décrivent un Parent GLPI central et sept entités locales d'inventaire de stock, avec accès navigateur nominatif et connexions LAN/VPN/HTTPS. Cette intention est documentée dans `Seven_Entity_Stock_Architecture.md` et le modèle `glpi_entity_stock_mapping.csv`; les deux diagrammes source sont conservés dans `docs/images/glpi-stock-architecture-01.webp` et `docs/images/glpi-stock-architecture-02.webp`. Le terme « agent » du schéma désigne l'opérateur humain connecté au navigateur, pas le logiciel GLPI Agent installé sur les ordinateurs. Les entités sont des périmètres logiques dans une même instance/base GLPI; elles ne constituent pas sept bases séparées. Le mapping des sites et responsables Stock-01…07 est laissé à validation, car les visuels ont des numérotations incohérentes et ne donnent pas la correspondance métier. L'application expose un écran pour les sept codes et une association admin d'ID GLPI, mais l'ID n'est pas vérifié contre le serveur. Les mouvements réels restent désactivés en HTTP 503, sans données synthétiques ni registre parallèle, jusqu'à identification/versionnement du plugin stock GLPI. Les droits récursifs, compatibilité et historique des mouvements doivent être testés sur recette. Aucun stock, compte, entité ou serveur réel n'a été configuré.

## 17. Perspectives
Ajouter contrat GLPI versionné et tests contre instance de recette pour le module stock, activer les mouvements uniquement après validation, authentification institutionnelle, permissions GLPI individuelles, CSRF complet, cookies Secure confirmés, audit/logging et rate limits distribués, OpenAPI, migrations versionnées, tests navigateur et CI, gestion des commentaires/updates, tableau de bord stock réel et tests d'isolation. Compléter la mise en œuvre du GLPI central (agents, SNMP, inventaire labos, stock, seuils et réservations) suivant le runbook déjà fourni.

## 18. Conclusion
Une application pilote exécutable, interface et backend sont présents et les onze tests unitaires déclarés passent dans le workspace. L'intégration GLPI et IA est codée mais non vérifiée contre des services réels, car aucune instance ni clé n'est disponible. Ce livrable ne constitue donc ni une installation de production ni une preuve de cloisonnement départemental. L'étape suivante est une validation autorisée sur GLPI de test avec comptes de moindre privilège, puis revue de sécurité et recette métier FSS.

## 19. Annexes
- `API.md`: routes, formats et limites d'autorisation.
- `Architecture.md`: flux et frontières de confiance.
- `Deployment_and_Operations_Runbook.md`: roadmap et procédures FSS.
- `.env.example`: noms de variables sans valeurs secrètes.
- `tests/test_app.py`: tests automatisés disponibles.
