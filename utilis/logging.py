import logging
import os
from datetime import datetime


class MigrationLogger:
    def __init__(self):
        self.logs_dir = "logs"
        self.setup_logs_directory()
        self.setup_loggers()

    def setup_logs_directory(self):
        """Crée le dossier logs s'il n'existe pas."""
        if not os.path.exists(self.logs_dir):
            os.makedirs(self.logs_dir)

    def setup_loggers(self):
        """Configure les loggers pour info, warning et error."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Logger pour les informations
        self.info_logger = self._create_logger("info", f"{self.logs_dir}/info_{timestamp}.log", logging.INFO)

        # Logger pour les avertissements
        self.warning_logger = self._create_logger("warning", f"{self.logs_dir}/warning_{timestamp}.log",
                                                  logging.WARNING)

        # Logger pour les erreurs
        self.error_logger = self._create_logger("error", f"{self.logs_dir}/error_{timestamp}.log", logging.ERROR)

    def _create_logger(self, name, log_file, level):
        """Crée un logger avec un fichier de sortie spécifique."""
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Handler pour écrire dans un fichier avec encodage UTF-8
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger

    def log_info(self, message):
        """Enregistre un message d'information."""
        self.info_logger.info(message)

    def log_warning(self, message):
        """Enregistre un message d'avertissement."""
        self.warning_logger.warning(message)

    def log_error(self, message):
        """Enregistre un message d'erreur."""
        self.error_logger.error(message)

    def start_log(self):
        """Démarre la journalisation."""
        self.log_info("Début de la migration des données.")

    def end_log(self, size_folder_source, total_files, total_folders, total_contenu_copied, error_logs):
        """Termine la journalisation et enregistre les statistiques."""
        self.log_info(f"Taille totale du dossier source : {size_folder_source} octets")
        self.log_info(f"Nombre total de fichiers : {total_files}")
        self.log_info(f"Nombre total de dossiers : {total_folders}")
        self.log_info(f"Nombre de fichiers copiés : {total_contenu_copied}")

        # Enregistrer les erreurs
        for error_type, errors in error_logs.items():
            if errors:
                self.log_error(f"{error_type}: {len(errors)} erreurs")
                for error in errors:
                    self.log_error(f"- {error}")

        self.log_info("Fin de la migration des données.")