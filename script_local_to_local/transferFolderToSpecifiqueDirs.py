import os
import shutil
import logging
from datetime import datetime

# Configuration du logging
logging.basicConfig(filename='../delivery.log', level=logging.INFO, format='%(asctime)s - %(message)s')


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


def deliver_packages(packages, mapping):
    """Copie chaque dossier vers sa cible spécifique."""
    for package in packages:
        target_dir = get_target_dir(package, mapping)
        if not target_dir:
            logging.error(f"Aucune cible trouvée pour le package : {package}")
            continue

        try:
            # Crée le chemin de destination
            relative_path = os.path.relpath(package, os.path.dirname(package))
            destination = os.path.join(target_dir, relative_path)

            # Copie le dossier
            shutil.copytree(package, destination)
            logging.info(f"Livraison réussie: {package} -> {destination}")
        except Exception as e:
            logging.error(f"Erreur lors de la livraison de {package}: {e}")


def main():
    # Dossier source (où se trouvent les dossiers à copier)
    source_dir = "chemin/vers/source"

    # Mapping des packages vers leurs cibles spécifiques
    # Exemple : { "chemin/vers/source/dossier1": "chemin/vers/cible1", ... }
    package_mapping = {
    r"D:\\handleFile\\D1": r"D:\\handleFile\\D1",
    r"D:\\handleFile\\D2": "D:\\handleFile\\D2",
    r"D:\\handleFile\\D3": r"D:\\handleFile\\D3"
}

    # Préparation des colis
    packages = prepare_packages(source_dir)

    # Livraison des colis
    deliver_packages(packages, package_mapping)


if __name__ == "__main__":
    main()