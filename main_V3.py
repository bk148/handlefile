import json
from pathlib import Path
from rich.console import Console

from apiAuthenfication.msgraphAuth import TokenGenerator
from settings.config import app_id, client_secret, tenant_id, scopes, proxy, migration_Route_Map
from controller.controller_transfer import ControllerGraphTransfer
from view import ConsoleView

console = Console()

# Load the JSON data
with open(migration_Route_Map, 'r', encoding='utf-8') as file:
    data = json.load(file)

# Obtenir le token d'accès
token_generator = TokenGenerator(app_id, client_secret, tenant_id, proxy, scopes)
view = ConsoleView()  # Utilisation de la vue console
controller = ControllerGraphTransfer(token_generator, proxy, view)

# Itérer sur chaque équipe et transférer les dossiers
for team_name, team_info in data.items():
    team_id = team_info["team_id"]
    channel_id = team_info["destination_to"]["channel_id"]
    site_id = team_info["destination_to"]["site_id"]

    console.print(f"Début de la migration pour l'équipe: {team_name}")

    for folder_name, folder_path in team_info["folders_to_migrate"].items():
        DEPOT_DATA_DIRECTORY_PATH = Path(folder_path)
        controller.transfer_data_folder_to_channel(team_id, channel_id, site_id, DEPOT_DATA_DIRECTORY_PATH)

    console.print(f"Migration terminée pour l'équipe: {team_name}")

console.print("Data transfer completed for all teams.")