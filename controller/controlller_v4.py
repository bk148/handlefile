import os
import time
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn

# Importations des modules personnalisés
from model.model_transfer import ModelGraphTransfer
from utilis.logger_v4 import MigrationLogger

class ControllerGraphTransfer:
    def __init__(self, token_generator, proxy, logger):
        """
        Initialise le contrôleur avec le générateur de token, le proxy et le logger.
        :param token_generator: Instance de TokenGenerator pour obtenir les tokens d'accès.
        :param proxy: Proxy à utiliser pour les requêtes.
        :param logger: Instance de MigrationLogger pour la journalisation.
        """
        self.graph_api = ModelGraphTransfer(token_generator, proxy, logger)  # Passe le logger au modèle
        self.console = Console()
        self.logger = logger  # Stocke le logger pour une utilisation locale

    def create_folder(self, site_id, parent_item_id, folder_name):
        """
        Crée un dossier dans le canal Teams.
        :param site_id: ID du site SharePoint.
        :param parent_item_id: ID du dossier parent.
        :param folder_name: Nom du dossier à créer.
        :return: Réponse de l'API ou None en cas d'erreur.
        """
        self.logger.log_general_event(f"Tentative de création du dossier {folder_name}.")
        result = self.graph_api.create_folder(site_id, parent_item_id, folder_name)
        if result:
            self.logger.log_success(f"Dossier {folder_name} créé avec succès.", context=f"Site ID: {site_id}, Parent Item ID: {parent_item_id}")
        else:
            self.logger.log_file_error(f"Échec de la création du dossier {folder_name}.", context=f"Site ID: {site_id}, Parent Item ID: {parent_item_id}")
        return result

    def transfer_data_folder_to_channel(self, group_id, channel_id, site_id, depot_data_directory_path):
        """
        Transfère un dossier entier vers un canal Teams.
        :param group_id: ID du groupe Teams.
        :param channel_id: ID du canal Teams.
        :param site_id: ID du site SharePoint.
        :param depot_data_directory_path: Chemin du dossier local à transférer.
        """
        # Démarrer la mesure du temps et la journalisation
        self.logger.log_general_event(f"Début du transfert pour Group ID: {group_id}, Channel ID: {channel_id}, Site ID: {site_id}")
        start_time = time.time()

        self.console.print("[green]Starting file transfer...[/green]")

        # Calculer le nombre total de fichiers et le volume des données
        total_initial = sum([len(files) for _, _, files in os.walk(depot_data_directory_path)])
        total_volume = sum([os.path.getsize(os.path.join(root, file)) for root, _, files in os.walk(depot_data_directory_path) for file in files])

        self.logger.log_general_event(f"Total des fichiers à transférer: {total_initial}")
        self.logger.log_general_event(f"Volume total des données: {total_volume / (1024 * 1024):.2f} MB")

        # Démarrer le transfert
        size_folder_source, total_files, total_folders, total_copied = self.graph_api.transfer_data_folder_to_channel(
            group_id, channel_id, site_id, depot_data_directory_path
        )

        # Calculer et afficher la durée
        end_time = time.time()
        duration = end_time - start_time
        self.console.print(f"[blue]Total transfer duration: {duration:.2f} seconds[/blue]")
        self.logger.log_general_event(f"Durée totale du transfert: {duration:.2f} secondes")

        # Terminer la journalisation
        self.logger.log_general_event(f"Transfert terminé. Fichiers copiés: {total_copied}, Erreurs: {len(self.graph_api.error_logs)}")
        self.logger.log_general_event(f"Taille du dossier source: {size_folder_source / (1024 * 1024):.2f} MB")
        self.logger.log_general_event(f"Total des fichiers: {total_files}")
        self.logger.log_general_event(f"Total des dossiers: {total_folders}")