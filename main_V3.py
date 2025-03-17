import json
from pathlib import Path
from rich.console import Console

from apiAuthenfication.msgraphAuth import TokenGenerator
from settings.config import app_id, client_secret, tenant_id, scopes, proxy, migration_Route_Map
from controller.controller_transfer import ControllerGraphTransfer
from logging_config import setup_logging

# Configuration du logging (sans affichage en console par défaut)
setup_logging(enable_console_logs=False)  # Changez à True pour activer les logs en console

console = Console()

# Load the JSON data
with open(migration_Route_Map, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Obtenir le token d'accès
token_generator = TokenGenerator(app_id, client_secret, tenant_id, proxy, scopes)
controller = ControllerGraphTransfer(token_generator, proxy)

# Itérer sur chaque équipe et transférer les dossiers
for team_name, team_info in data.items():
    team_id = team_info["team_id"]
    channel_id = team_info["destination_to"]["channel_id"]
    site_id = team_info["destination_to"]["site_id"]

    console.print(f"[bold cyan]Début de la migration pour l'équipe: {team_name}[/bold cyan]")

    for folder_name, folder_path in team_info["folders_to_migrate"].items():
        DEPOT_DATA_DIRECTORY_PATH = Path(folder_path)
        console.print(f"[bold blue]Transfert du dossier: {folder_name} situé à {folder_path}[/bold blue]")
        controller.transfer_data_folder_to_channel(team_id, channel_id, site_id, DEPOT_DATA_DIRECTORY_PATH)

    console.print(f"[bold green]Migration terminée pour l'équipe: {team_name}[/bold green]")

console.print("[bold green]Data transfer completed for all teams.[/bold green]")