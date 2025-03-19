import logging
import os
from logging.handlers import RotatingFileHandler

class MigrationLogger:
    def __init__(self, log_directory="logs"):
        """
        Initialise le système de journalisation avec des catégories spécifiques.
        :param log_directory: Répertoire où les fichiers de logs seront stockés.
        """
        self.log_directory = log_directory
        self._ensure_log_directory_exists()

        # Configuration des logs
        self._setup_loggers()

    def _ensure_log_directory_exists(self):
        """Crée le répertoire de logs s'il n'existe pas."""
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)

    def _setup_loggers(self):
        """Configure les différents loggers avec des handlers spécifiques."""
        # Formateur de logs commun
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        # Logger pour les fichiers en erreur
        self.file_error_logger = self._create_logger(
            name="file_error_logger",
            log_file=os.path.join(self.log_directory, "file_errors.log"),
            level=logging.ERROR,
            formatter=formatter
        )

        # Logger pour les problèmes réseau
        self.network_logger = self._create_logger(
            name="network_logger",
            log_file=os.path.join(self.log_directory, "network.log"),
            level=logging.INFO,
            formatter=formatter
        )

        # Logger général pour les événements
        self.general_logger = self._create_logger(
            name="general_logger",
            log_file=os.path.join(self.log_directory, "general.log"),
            level=logging.INFO,
            formatter=formatter
        )

        # Logger pour les succès
        self.success_logger = self._create_logger(
            name="success_logger",
            log_file=os.path.join(self.log_directory, "success.log"),
            level=logging.INFO,
            formatter=formatter
        )

    def _create_logger(self, name, log_file, level, formatter):
        """
        Crée un logger avec un handler de fichier rotatif.
        :param name: Nom du logger.
        :param log_file: Chemin du fichier de log.
        :param level: Niveau de log (ex: logging.INFO, logging.ERROR).
        :param formatter: Formateur de logs.
        :return: Instance de logger configurée.
        """
        logger = logging.getLogger(name)
        logger.setLevel(level)

        # Handler pour écrire dans un fichier avec rotation
        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB par fichier
            backupCount=5  # Conserve les 5 derniers fichiers
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def log_file_error(self, message, context=None):
        """
        Journalise une erreur liée aux fichiers.
        :param message: Message d'erreur.
        :param context: Contexte supplémentaire (ex: fichier concerné, chemin, etc.).
        """
        if context:
            message = f"{message} | Context: {context}"
        self.file_error_logger.error(message)

    def log_network_error(self, message, status_code=None, url=None):
        """
        Journalise une erreur réseau ou une réponse HTTP.
        :param message: Message d'erreur ou de succès.
        :param status_code: Code de statut HTTP (ex: 401, 429).
        :param url: URL concernée.
        """
        if status_code:
            message = f"{message} | Status Code: {status_code}"
        if url:
            message = f"{message} | URL: {url}"
        self.network_logger.error(message)

    def log_network_success(self, message, status_code=None, url=None):
        """
        Journalise une réussite réseau.
        :param message: Message de succès.
        :param status_code: Code de statut HTTP (ex: 200).
        :param url: URL concernée.
        """
        if status_code:
            message = f"{message} | Status Code: {status_code}"
        if url:
            message = f"{message} | URL: {url}"
        self.network_logger.info(message)

    def log_general_event(self, message):
        """
        Journalise un événement général.
        :param message: Message à journaliser.
        """
        self.general_logger.info(message)

    def log_success(self, message, context=None):
        """
        Journalise une opération réussie.
        :param message: Message de succès.
        :param context: Contexte supplémentaire (ex: fichier transféré, dossier créé).
        """
        if context:
            message = f"{message} | Context: {context}"
        self.success_logger.info(message)