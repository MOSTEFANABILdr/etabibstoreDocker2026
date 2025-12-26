# Protocol de Synchronisation des Données Médicaments
**Version:** 1.0 (2025)
**Cible:** Développeurs Desktop / Clients Lourds

Ce document décrit l'algorithme implémenté côté serveur (Django) pour propager les mises à jour des médicaments vers les applications clientes (Desktop).

## 1. Vue d'ensemble (Architecture)
Le système utilise une approche de **Réplication par Logs de Requêtes (Query Log Replication)**.
Au lieu d'envoyer l'objet modifié, le serveur enregistre la **requête SQL exacte** nécessaire pour reproduire la modification sur le client.

*   **Type**: Pull (Le client doit venir chercher les changements).
*   **Format**: Requêtes SQL brutes (MySQL/SQLite compatible).
*   **Table Pivot**: `drugs_changedrugs`.

## 2. Algorithme Côté Serveur
À chaque modification (Création ou Mise à jour) d'une donnée sensible (Médicament, Forme, Laboratoire, etc.), un "Signal" Django intercepte l'événement `pre_save`.

### Le Processus (Trigger)
1.  **Détection** : L'administrateur modifie un médicament.
2.  **Construction SQL** : Le serveur génère dynamiquement la requête SQL correspondante.
    *   *Exemple Update* : `UPDATE medicament SET dosage='500mg', ... WHERE unique_id='xyz';`
    *   *Exemple Insert* : `INSERT INTO medicament SET unique_id='xyz', dosage='500mg'...;`
3.  **Stockage** : Cette requête est stockée dans la table `ChangeDrugs`.
    *   **Query** : La chaîne SQL complète.
    *   **Date** : Timestamp de la modification.

### Modèles Surveillés
Les tables suivantes déclenchent une synchronisation (voir `drugs/signals.py`) :
*   `medicament`
*   `medicament_cnas`
*   `nom_commercial`
*   `medic_categorie`
*   ... et autres tables référentielles.

## 3. Implémentation Côté Client (Desktop)
Le client doit implémenter un algorithme de **Polling (Vérification périodique)**.

### Algorithme de Synchronisation
1.  **Stockage Local d'État** : Le client doit garder en mémoire (ou en base) le `timestamp` de sa dernière synchronisation réussie (ex: `last_sync_date`).
2.  **Appel API** : Périodiquement (ex: au démarrage ou toutes les X minutes), le client appelle l'API de synchronisation.
    *   *Endpoint* : `/api/drugs/sync/` (À vérifier selon routes existantes)
    *   *Paramètre* : `?since=<last_sync_date>`
3.  **Traitement** :
    *   Le serveur renvoie une liste de requêtes SQL (ordonnées chronologiquement) créées après `last_sync_date`.
4.  **Exécution** :
    *   Le client ouvre une transaction locale.
    *   Il exécute chaque requête SQL reçue sur sa base locale.
    *   Si tout est OK : Il met à jour son `last_sync_date`.
    *   Si erreur : Il annule la transaction (Rollback) et réessaiera plus tard.

## 4. Structure de Données (Référence)
La table d'échange sur le serveur :

```sql
CREATE TABLE drugs_changedrugs (
    id CHAR(32) NOT NULL PRIMARY KEY,
    query VARCHAR(3000) NOT NULL,
    date_mise_a_jour DATETIME(6) NOT NULL
);
```

## 5. Exemple de Flux
1.  **Serveur** : Admin change "Doliprane 500" en "Doliprane 1000".
2.  **Serveur** : Crée `UPDATE medicament SET dosage='1000' ...` dans `ChangeDrugs`.
3.  **Client** : Appelle l'API "Donne-moi les news depuis hier".
4.  **Client** : Reçoit le SQL `UPDATE...`.
5.  **Client** : Exécute le SQL. Sa base locale affiche maintenant "1000".

---
**Note pour le dev Desktop :**
Ce système suppose que votre base locale a la **même structure** que la base serveur. Si vous changez le schéma local, la synchronisation SQL échouera.
