# Architecture de stock GLPI — serveur central et 7 entités locales

## Modèle cible d'après les schémas fournis
- **Une instance GLPI centrale** hébergée sur le réseau FSS, accessible via HTTPS sur LAN ou VPN; une base MariaDB/MySQL centralisée et des sauvegardes sont administrées par l'équipe IT.
- **Entité racine (Parent)**: gouvernance, catalogue commun, rapports globaux et administration; les opérations courantes dans les stocks locaux ne sont pas faites dans le Parent sauf autorisation explicite.
- **Sept entités enfants** représentant chacune un stock/site autorisé. Identifiants provisoires: `Stock-01` à `Stock-07`. Les départements/bâtiments correspondant à ces codes ne sont pas connus et doivent être décidés avec les responsables FSS avant création. Le périmètre des 7 entités de stock n'est pas forcément identique aux quatre départements académiques du cahier des charges.
- **Utilisateurs humains** (magasiniers/responsables) accèdent par navigateur avec des comptes individuels, profils et périmètres d'entité adaptés. Le terme « agent » dans les visuels signifie ici un utilisateur opérateur, et non GLPI Agent logiciel d'inventaire de postes. L'agent GLPI d'inventaire est un composant distinct déployé sur les postes et ne sert pas à enregistrer les sorties de stock.
- Les utilisateurs autorisés enregistrent chaque réception, sortie, transfert ou ajustement dans l'entité concernée. L'administration centrale consulte les agrégats et mouvements consolidés selon le profil.

## Précisions techniques et garde-fous
1. Les entités GLPI sont un cloisonnement logique au sein d'une instance/base GLPI; ce ne sont pas sept serveurs, sept bases de données, ni une synchronisation asynchrone de bases locales.
2. Définir l'héritage de l'entité, les profils, groupes et droits (lecture/création/modification/suppression, transfert et visibilité récursive) avec moindre privilège. L'accès à un Parent avec droits récursifs peut inclure les enfants: ne pas attribuer récursivité aux utilisateurs locaux. Tester deux utilisateurs de stocks distincts et un administrateur consolidé.
3. Un compte partagé par plusieurs magasiniers est à éviter: il détruit la traçabilité nominative. Un rôle local peut être réutilisé, mais chaque personne a son compte.
4. Confirmer la version de GLPI et la solution exacte de gestion des stocks: fonctionnalités natives réellement disponibles, plugin maintenu compatible, ou module approuvé. Les entrées/sorties, lots, unités, seuils, alertes et transferts indiqués par le diagramme ne sont pas garantis par le seul noyau GLPI. Piloter les flux avant d'importer les soldes réels.
5. Les sept « agents » numérotés des images ne sont pas cohérents: une version omet Agent 04 et les mentions de stocks locaux ont des numéros décalés. Ce document normalise les étiquettes en Stock-01…Stock-07; l'affectation métier est à valider, ne pas déduire depuis l'image.
6. Le service Python de ce projet est une interface d'assistance séparée, pas le serveur GLPI, le moteur de stock, ni un client synchronisant des bases locales. GLPI reste la source faisant autorité. Aucun écran de stock ou mouvements n'est encore implémenté dans l'application pilote.

## Plan de configuration
1. FSS valide la liste des 7 sites/stocks, leurs responsables, entrepôts, unités, seuils et règles de transfert.
2. L'administrateur crée et teste le Parent et sept enfants dans une instance GLPI de recette; décide la récursivité et le comportement d'héritage pour chaque profil.
3. Crée profils dédiés: magasinier local (une entité), responsable local (vue de son entité), centralisateur (lecture consolidée autorisée), administrateur GLPI (administration technique réservée à l'IT).
4. Affecte les comptes nominatifs aux entités et groupes appropriés; interdit les identifiants partagés.
5. Teste isolement: compte Stock-01 ne peut ni lire ni modifier Stock-02; responsable central autorisé voit le rapport consolidé; audit des mouvements identifie la personne.
6. Vérifie réception/sortie/transfert/annulation, seuils et alertes, export/rapport, sauvegarde/restauration et historique. Utilise des données synthétiques en recette.
7. Après recette et accord métier, importe les soldes d'ouverture validés, puis rapproche les quantités avec un inventaire physique.

## Matrice de départ (à faire valider)
| Entité | Code provisoire | Correspondance site/département | Responsable métier | Profil local | Seuils définis |
|---|---|---|---|---|---|
| Parent | FSS | Faculté / central | À désigner | Administration centrale | Sans objet |
| Enfant 1 | Stock-01 | À valider | À désigner | Magasinier local | À définir |
| Enfant 2 | Stock-02 | À valider | À désigner | Magasinier local | À définir |
| Enfant 3 | Stock-03 | À valider | À désigner | Magasinier local | À définir |
| Enfant 4 | Stock-04 | À valider | À désigner | Magasinier local | À définir |
| Enfant 5 | Stock-05 | À valider | À désigner | Magasinier local | À définir |
| Enfant 6 | Stock-06 | À valider | À désigner | Magasinier local | À définir |
| Enfant 7 | Stock-07 | À valider | À désigner | Magasinier local | À définir |

## Portée non vérifiée
Aucune configuration n'a été appliquée à une instance GLPI réelle. Les images sont des schémas de conception et non la preuve qu'un serveur, des comptes, sept entités ou mouvements de stock ont déjà été créés. Valider chaque choix avec l'IT et les responsables métier de FSS.