#!/bin/bash

# deploy_step_3.sh
# Script d'automatisation pour l'étape 3 : Extract Data & Move Configurations
# Ce script doit être exécuté sur le serveur de production (dans le dossier offline_deployment_package si possible)

# Configuration par défaut
BASE_DIR="/mnt/live_data/etabib_project"
PACKAGE_DIR="${BASE_DIR}/offline_deployment_package"

# Couleurs pour les logs
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO] $1${NC}"
}

log_error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

log_warn() {
    echo -e "${YELLOW}[WARN] $1${NC}"
}

# Vérification des droits root
if [ "$EUID" -ne 0 ]; then 
  log_error "Ce script doit être exécuté en tant que root (sudo)."
  exit 1
fi

# Détection du contexte d'exécution
CURRENT_DIR=$(pwd)
if [ -f "$CURRENT_DIR/mysql_tuning.cnf" ]; then
    PACKAGE_DIR="$CURRENT_DIR"
    log_info "Exécution depuis le dossier du package : $PACKAGE_DIR"
elif [ -d "$PACKAGE_DIR" ]; then
    log_info "Dossier du package détecté à $PACKAGE_DIR. Déplacement..."
    cd "$PACKAGE_DIR" || exit 1
else
    log_error "Impossible de trouver le package de déploiement."
    log_error "Veuillez exécuter ce script depuis le dossier contenant mysql_tuning.cnf et les archives."
    exit 1
fi

log_info "Début de l'étape 3..."

# 1. Déplacer la configuration de tuning MySQL
if [ -f "mysql_tuning.cnf" ]; then
    log_info "Déplacement de mysql_tuning.cnf vers ../"
    cp mysql_tuning.cnf ../
else
    log_warn "Fichier mysql_tuning.cnf introuvable ! (Step ignoré à la demande de l'utilisateur)"
    # exit 1  <-- Désactivé pour bypass
fi

# 2. Extraire les fichiers Media, Static et Jitsi
for archive in media_backup.tar.gz static_backup.tar.gz jitsi_config_backup.tar.gz; do
    if [ -f "$archive" ]; then
        log_info "Extraction de $archive vers ../"
        tar -xzf "$archive" -C ../
    else
        log_warn "Archive $archive manquante (peut-être déjà extraite ?)"
    fi
done

# 3. Extraire les données Ollama (si présentes)
if [ -f "ollama_data_backup.tar.gz" ]; then
    log_info "Extraction de ollama_data_backup.tar.gz vers ../"
    tar -xzf ollama_data_backup.tar.gz -C ../
else
    log_info "Pas de backup Ollama trouvé (ollama_data_backup.tar.gz), étape ignorée."
fi

log_info "Vérification basique des fichiers extraits..."
ls -l ../mysql_tuning.cnf 2>/dev/null
ls -ld ../media ../static 2>/dev/null

log_info "Étape 3 terminée avec succès."
