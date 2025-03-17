import logging
from logging.handlers import RotatingFileHandler
import os

# Dossiers de logs
LOG_DIR = "logs"
ERROR_CATEGORIES = [
    "Connection Error", "Authentication Error", "Data Format Error",
    "Access Rights Error", "Network Error", "Quota Error",
    "File Error", "Cyclic Redundancy Error", "Ignored Files"
]

def setup_logging():
    # Créer le dossier de logs s'il n'existe pas
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Configuration du logging principal (transfer.log)
    log_file = os.path.join(LOG_DIR, "transfer.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=2),  # 5 Mo par fichier, 2 backups
            logging.StreamHandler()  # Afficher les logs dans la console
        ]
    )

    # Configuration des logs par catégorie
    for category in ERROR_CATEGORIES:
        category_log_file = os.path.join(LOG_DIR, f"{category.lower().replace(' ', '_')}.log")
        category_handler = RotatingFileHandler(category_log_file, maxBytes=5 * 1024 * 1024, backupCount=2)
        category_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        category_logger = logging.getLogger(category)
        category_logger.setLevel(logging.ERROR)  # Seuls les logs de niveau ERROR sont enregistrés
        category_logger.addHandler(category_handler)

    # Logger de démarrage
    logging.info("Logging configuration is set up.")