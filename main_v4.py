import json
import os
from pathlib import Path
import requests
from rich.console import Console

# Importations des modules personnalisés
from apiAuthenfication.msgraphAuth import TokenGenerator
from settings.config import app_id, client_secret, tenant_id, scopes, proxy
from settings.config import migration_Route_Map
from controler.controller_transfer import ControllerGraphTransfer
from utilis.logger_v4 import MigrationLogger  # Import de la nouvelle classe de journalisation

# Initialisation de la console Rich pour l'affichage coloré
console = Console()

# Charger les données de configuration depuis le fichier JSON
with open(migration_Route_Map, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Initialisation du logger
logger = MigrationLogger(log_directory="logs")

# Obtenir le token d'accès via TokenGenerator
token_generator = TokenGenerator(app_id, client_secret, tenant_id, proxy, scopes)

# Initialisation du contrôleur avec le token, le proxy et le logger
controller = ControllerGraphTransfer(token_generator, proxy, logger)

# Itérer sur chaque équipe et transférer les dossiers
for team_name, team_info in data.items():
    team_id = team_info["team_id"]
    channel_id = team_info["destination_to"]["channel_id"]
    site_id = team_info["destination_to"]["site_id"]

    console.print(f"[bold green]Début de la migration pour l'équipe: {team_name}[/bold green]")
    logger.log_general_event(f"Début de la migration pour l'équipe: {team_name}")

    for folder_name, folder_path in team_info["folders_to_migrate"].items():
        DEPOT_DATA_DIRECTORY_PATH = Path(folder_path)

        console.print(f"[bold blue]Transfert du dossier: {folder_name} situé à {folder_path}[/bold blue]")
        logger.log_general_event(f"Transfert du dossier: {folder_name} situé à {folder_path}")

        # Démarrer le transfert du dossier
        controller.transfer_data_folder_to_channel(team_id, channel_id, site_id, DEPOT_DATA_DIRECTORY_PATH)

    console.print(f"[bold green]Migration terminée pour l'équipe: {team_name}[/bold green]")
    logger.log_general_event(f"Migration terminée pour l'équipe: {team_name}")

console.print("[bold green]Data transfer completed for all teams.[/bold green]")
logger.log_general_event("Data transfer completed for all teams.")