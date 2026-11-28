# État du module de stock (mise à jour suivant les 7 entités)

## Livré dans l'application pilote
- Catalogue logique des sept codes `STOCK-01` à `STOCK-07`, initialisé automatiquement dans SQLite sans quantités, mouvements ou faux soldes.
- Écran Stocks (7) : expose toutes les entités aux administrateurs et uniquement le code affecté aux autres comptes.
- Écran Administrateur : association d'un code à un identifiant GLPI saisi par un admin; contrôles du code, nom, entier et unicité, trace d'audit.
- Création de compte admin peut attribuer un `stock_entity_code` (via `POST /api/admin/users`).
- Les anciens fichiers `users` reçoivent une colonne `stock_entity_code` via migration additive, sans supprimer les comptes.
- `GET /api/stocks` refuse explicitement les opérations avec HTTP 503 tant qu'un connecteur de stock GLPI compatible n'est pas choisi et testé. Il ne fait aucune écriture dans un registre parallèle.

## Ce que l'association ne garantit pas
Le champ `glpi_entity_id` est une valeur fournie par un administrateur et enregistrée comme configuration locale. L'application ne peut pas confirmer que l'entité existe, qu'elle représente le bon magasin, ni que les profils/récursivités GLPI appliquent l'isolation voulue. L'écran la signale donc comme « ID à vérifier dans GLPI », et non comme entité vérifiée.

## Blocage pour l'activation des mouvements réels
Le responsable a confirmé que GLPI doit rester la source de vérité, mais la version GLPI et le plugin/API qui réalise la gestion d'entrées, sorties, transferts, seuils et lots ne sont pas encore connus. Le noyau GLPI/API REST n'offre pas forcément le modèle d'historique stock demandé. Il est dangereux d'inventer des URL/payloads ou de modifier les stocks avant validation de la version et du module. Quand ces détails seront disponibles, ajouter un adaptateur serveur avec contrat versionné et tests mockés, puis test de recette sur une instance GLPI autorisée.

## Configuration pilote
1. Créer les sept entités enfants dans GLPI recette et enregistrer la correspondance réelle dans l'écran admin.
2. Affecter l'utilisateur avec `stock_entity_code` via l'API d'administration, un code par opérateur local.
3. Vérifier les accès GLPI avec comptes dédiés Stock-01 et Stock-02 et un compte central admin.
4. Ne pas enregistrer de mouvements tant que la route d'API du plugin et son comportement d'audit ne sont pas validés.

API admin: `GET/POST /api/admin/entities`. Endpoint stock: `GET /api/stocks` renvoie actuellement `503` délibérément. Voir aussi `Seven_Entity_Stock_Architecture.md`.