"""
== Copié des dossiers vers un channel teams ==

créer un script qui copie des dossiers vers une cible en s'inspirant du modèle de livraison de lettres ou colis par un facteur,
structure du script:

1) Préparation des données : Identifier les dossiers à copier (les "colis").

2) Organisation des livraisons : Déterminer la cible (le "destinataire").

3) Livraison : Copier les dossiers vers la cible.

4) Suivi : Vérifier que la copie a réussi et enregistrer les logs.

---------------------------Améliorations possibles------------------------------- :
1) Gestion des conflits : Ajouter une logique pour gérer les dossiers déjà existants dans la cible.

2) Multithreading : Utiliser le multithreading pour accélérer la copie si le nombre de dossiers est important.

3) Interface utilisateur : Ajouter une interface utilisateur pour sélectionner les dossiers source et cible.

"""
import os
import shutil
import logging
import statsmodels
from datetime import datetime
from pathlib import Path

from rich.console import Console

console = Console()

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


def deliver_packages(packages, target_dir):
    """Copie les dossiers vers la cible (livraison)."""
    for package in packages:
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
    source_dir = r"/Depot"

    # Dossier cible (où les dossiers seront copiés)
    target_dir = r"/Depot/Destination"

    # Préparation des colis
    packages = prepare_packages(source_dir)

    # Livraison des colis
    deliver_packages(packages, target_dir)


if __name__ == "__main__":
    main()
# def transfer(folder_name, team_name, location):
#
#     pass

# console = Console()
# path_data = r"D:\handleFile\Depot"
# for root, dirs, files  in os.walk(path_data):
#     root_path = Path(root)
#     for file in files:
#         file_path = root_path / file
#         print(file_path)
