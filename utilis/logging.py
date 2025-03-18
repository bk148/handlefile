import logging
import os
from datetime import datetime

class MigrationLogger:
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        self.start_time = None
        self.end_time = None
        self.total_files = 0
        self.total_folders = 0
        self.total_copied = 0
        self.size_folder_source = 0
        self.error_logs = {}

        # Créer le répertoire de logs s'il n'existe pas
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        # Configurer le logger principal
        self.logger = logging.getLogger("MigrationLogger")
        self.logger.setLevel(logging.INFO)

        # Formateur de logs
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Handler pour le fichier de log principal
        log_file = os.path.join(self.log_dir, "Migration.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        # Handlers pour les fichiers d'erreur spécifiques
        self.error_handlers = {
            "Connection Error": self._create_error_handler("ConnectionError.log"),
            "Authentication Error": self._create_error_handler("AuthenticationError.log"),
            "Data Format Error": self._create_error_handler("DataFormatError.log"),
            "Access Rights Error": self._create_error_handler("AccessRightsError.log"),
            "Network Error": self._create_error_handler("NetworkError.log"),
            "Quota Error": self._create_error_handler("QuotaError.log"),
            "File Error": self._create_error_handler("FileError.log"),
            "Cyclic Redundancy Error": self._create_error_handler("CyclicRedundancyError.log"),
            "Ignored Files": self._create_error_handler("IgnoredFiles.log"),
        }

    def _create_error_handler(self, filename):
        """Crée un handler de fichier pour un type d'erreur spécifique."""
        handler = logging.FileHandler(os.path.join(self.log_dir, filename))
        handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        return handler

    def start_log(self):
        """Démarre la journalisation et enregistre l'heure de début."""
        self.start_time = datetime.now()
        self.logger.info(f"Migration started at {self.start_time}")

    def end_log(self, size_folder_source, total_files, total_folders, total_contenu_copied, error_logs):
        """Termine la journalisation et enregistre les statistiques."""
        self.end_time = datetime.now()
        self.size_folder_source = size_folder_source
        self.total_files = total_files
        self.total_folders = total_folders
        self.total_copied = total_contenu_copied
        self.error_logs = error_logs

        # Enregistrer les statistiques
        self.logger.info(f"Migration ended at {self.end_time}")
        self.logger.info(f"Total files to copy: {self.total_files}")
        self.logger.info(f"Files copied: {self.total_copied}")
        self.logger.info(f"Remaining files: {self.total_files - self.total_copied}")
        self.logger.info(f"Total folders created: {self.total_folders}")
        self.logger.info(f"Total data size: {self.size_folder_source / (1024 * 1024):.2f} MB")
        self.logger.info(f"Total duration: {(self.end_time - self.start_time).total_seconds():.2f} seconds")

        # Enregistrer les erreurs dans les fichiers spécifiques
        for error_type, errors in self.error_logs.items():
            if errors:
                handler = self.error_handlers.get(error_type)
                if handler:
                    logger = logging.getLogger(error_type)
                    logger.addHandler(handler)
                    for error in errors:
                        logger.error(error)
                    logger.removeHandler(handler)

        # Afficher un tableau récapitulatif
        self._print_summary_table()

    def _print_summary_table(self):
        """Affiche un tableau récapitulatif des statistiques."""
        from rich.table import Table
        from rich.console import Console

        console = Console()

        table = Table(title="Migration Summary", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Total files to copy", str(self.total_files))
        table.add_row("Files copied", str(self.total_copied))
        table.add_row("Remaining files", str(self.total_files - self.total_copied))
        table.add_row("Total folders created", str(self.total_folders))
        table.add_row("Total data size", f"{self.size_folder_source / (1024 * 1024):.2f} MB")
        table.add_row("Total duration", f"{(self.end_time - self.start_time).total_seconds():.2f} seconds")

        console.print(table)