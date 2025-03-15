import json
from pathlib import Path
from rich.console import Console

from model import ModelGraphTransfer
from controller import ControllerGraphTransfer
from view.view import TransferView
from settings.config import (
    app_id, client_secret, tenant_id, scopes, proxy, migration_Route_Map
)
from apiAuthentication.msgraphAuth import TokenGenerator

console = Console()

def main():
    try:
        # Initialisation des composants
        token_generator = TokenGenerator(app_id, client_secret, tenant_id, proxy, scopes)
        view = TransferView()
        controller = ControllerGraphTransfer(token_generator, proxy, view)

        # Chargement de la configuration
        with open(migration_Route_Map, 'r', encoding='utf-8') as f:
            migration_config = json.load(f)

        # Exécution des migrations
        for team_name, team_info in migration_config.items():
            view.show_section_header(f"Migration de l'équipe: {team_name}")
            controller.execute_migration(
                team_info["team_id"],
                team_info["destination_to"]["channel_id"],
                team_info["destination_to"]["site_id"],
                Path(team_info["folders_to_migrate"])
            )

        view.show_final_report(controller.get_stats())

    except Exception as e:
        view.log_critical_error(str(e))
        raise

if __name__ == "__main__":
    main()