import os
import shutil
import json
import logging
from concurrent.futures import ThreadPoolExecutor

# Configuration du logging
logging.basicConfig(filename='../delivery.log', level=logging.INFO, format='%(asctime)s - %(message)s')


def load_mapping(config_file):
    """Charge le mapping des packages vers leurs cibles depuis un fichier JSON."""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Erreur lors de la lecture du fichier de configuration : {e}")
        return {}


def prepare_packages(source_dir):
    """Prépare les dossiers à copier (les colis)."""
    packages = []
    for root, dirs, files in os.walk(source_dir):
        for dir_name in dirs:
            packages.append(os.path.join(root, dir_name))
    return packages


def get_target_dir(package, mapping):
    """Retourne le répertoire cible spécifique pour un package donné."""
    for source, target in mapping.items():
        if package.startswith(source):
            return target
    return None  # Si aucune correspondance n'est trouvée


def deliver_package(package, target_dir):
    """Copie un dossier vers sa cible spécifique."""
    try:
        # Crée le chemin de destination
        relative_path = os.path.relpath(package, os.path.dirname(package))
        destination = os.path.join(target_dir, relative_path)

        # Vérifie si le répertoire cible existe, sinon le crée
        os.makedirs(target_dir, exist_ok=True)

        # Copie le dossier
        shutil.copytree(package, destination)
        logging.info(f"Livraison réussie: {package} -> {destination}")
    except Exception as e:
        logging.error(f"Erreur lors de la livraison de {package}: {e}")


def deliver_packages(packages, mapping):
    """Copie chaque dossier vers sa cible spécifique en utilisant le multithreading."""
    with ThreadPoolExecutor(max_workers=5) as executor:  # 5 threads en parallèle
        futures = []
        for package in packages:
            target_dir = get_target_dir(package, mapping)
            if not target_dir:
                logging.error(f"Aucune cible trouvée pour le package : {package}")
                continue
            futures.append(executor.submit(deliver_package, package, target_dir))

        # Attendre que toutes les tâches soient terminées
        for future in futures:
            future.result()


def main():
    # Dossier source (où se trouvent les dossiers à copier)
    source_dir = r"/Depot"  # Remplacez par votre chemin source

    # Fichier de configuration JSON contenant le mapping des cibles
    config_file = r"/config.json"  # Remplacez par votre chemin de configuration

    # Chargement du mapping des cibles
    mapping = load_mapping(config_file)
    if not mapping:
        logging.error("Le mapping des cibles est vide ou invalide.")
        return

    # Préparation des colis
    packages = prepare_packages(source_dir)

    # Livraison des colis
    deliver_packages(packages, mapping)


if __name__ == "__main__":
    main()