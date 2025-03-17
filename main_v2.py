import json
from pathlib import Path
from rich.console import Console
from authentication import TokenGenerator
from settings.config import app_id, client_secret, tenant_id, scopes, proxy, migration_Route_Map
from controller import ControllerGraphTransfer

console = Console()

# Charger les données de migration
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

    console.print(f"[bold]Début de la migration pour l'équipe: {team_name}[/bold]")

    for folder_name, folder_path in team_info["folders_to_migrate"].items():
        DEPOT_DATA_DIRECTORY_PATH = Path(folder_path)
        console.print(f"Transfert du dossier: {folder_name} situé à {folder_path}")
        controller.transfer_data_folder_to_channel(team_id, channel_id, site_id, DEPOT_DATA_DIRECTORY_PATH)

    console.print(f"[bold]Migration terminée pour l'équipe: {team_name}[/bold]")

console.print("[bold green]Data transfer completed for all teams.[/bold green]")