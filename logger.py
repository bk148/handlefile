import logging
import unicodedata

class TransferLogger:
    def __init__(self, success_log_file: str = 'transfer_success.log', error_log_file: str = 'transfer_errors.log'):
        """
        Initialise le logger avec deux fichiers de log distincts pour les succès et les erreurs.
        Utilise l'encodage UTF-8 pour supporter tous les caractères Unicode.
        """
        # Créer un logger unique
        self.logger = logging.getLogger('TransferLogger')
        self.logger.setLevel(logging.INFO)  # Niveau de log global

        # Formatter commun pour les deux fichiers
        formatter = logging.Formatter('%(asctime)s - %(message)s')

        # Handler pour les succès (niveau INFO)
        success_handler = logging.FileHandler(success_log_file, mode='a', encoding='utf-8')  # Encodage UTF-8
        success_handler.setLevel(logging.INFO)
        success_handler.setFormatter(formatter)
        success_handler.addFilter(lambda record: record.levelno == logging.INFO)  # Filtrer uniquement les INFO

        # Handler pour les erreurs (niveau ERROR)
        error_handler = logging.FileHandler(error_log_file, mode='a', encoding='utf-8')  # Encodage UTF-8
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        error_handler.addFilter(lambda record: record.levelno == logging.ERROR)  # Filtrer uniquement les ERROR

        # Ajouter les handlers au logger
        self.logger.addHandler(success_handler)
        self.logger.addHandler(error_handler)

    def normalize_path(self, path: str) -> str:
        """
        Normalise un chemin de fichier pour supprimer les caractères Unicode problématiques.
        :param path: Chemin de fichier à normaliser.
        :return: Chemin de fichier normalisé.
        """
        return unicodedata.normalize('NFKD', path).encode('ascii', 'ignore').decode('ascii')

    def log_success(self, item_path: str):
        """
        Enregistre un succès dans le fichier des succès.
        :param item_path: Chemin du fichier transféré avec succès.
        """
        normalized_path = self.normalize_path(item_path)  # Normaliser le chemin
        self.logger.info(f"SUCCÈS: {normalized_path}")

    def log_failure(self, item_path: str, reason: str):
        """
        Enregistre un échec dans le fichier des erreurs.
        :param item_path: Chemin du fichier en échec.
        :param reason: Raison de l'échec.
        """
        normalized_path = self.normalize_path(item_path)  # Normaliser le chemin
        self.logger.error(f"ÉCHEC: {normalized_path} - Raison: {reason}")