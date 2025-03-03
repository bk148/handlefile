import os
import json
import logging
import requests
from concurrent.futures import ThreadPoolExecutor

# Configuration du logging
logging.basicConfig(filename='delivery.log', level=logging.INFO, format='%(asctime)s - %(message)s')

# Configuration de l'API Microsoft Graph
CLIENT_ID = "votre_client_id"
CLIENT_SECRET = "votre_client_secret"
TENANT_ID = "votre_tenant_id"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["https://graph.microsoft.com/.default"]
GRAPH_URL = "https://graph.microsoft.com/v1.0"


def get_access_token():
    """Obtient un jeton d'accès pour l'API Microsoft Graph."""
    url = f"{AUTHORITY}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": " ".join(SCOPE),
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        logging.error(f"Erreur lors de l'obtention du jeton d'accès : {response.text}")
        return None


def upload_file_to_teams(file_path, folder_id, access_token):
    """Téléverse un fichier vers un dossier de canal Teams."""
    file_name = os.path.basename(file_path)
    url = f"{GRAPH_URL}/drives/{folder_id}/root:/{file_name}:/content"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream",
    }
    with open(file_path, "rb") as file:
        response = requests.put(url, headers=headers, data=file)
    if response.status_code in [200, 201]:
        logging.info(f"Fichier téléversé avec succès : {file_name} -> {folder_id}")
    else:
        logging.error(f"Erreur lors du téléversement de {file_name} : {response.text}")


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


def deliver_package(package, destination, access_token):
    """Téléverse un dossier vers un dossier de canal Teams."""
    for root, _, files in os.walk(package):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            upload_file_to_teams(file_path, destination["location"], access_token)


def deliver_packages(packages, mapping, access_token):
    """Téléverse chaque dossier vers sa cible spécifique en utilisant le multithreading."""
    with ThreadPoolExecutor(max_workers=5) as executor:  # 5 threads en parallèle
        futures = []
        for package in packages:
            destination = mapping.get(package)
            if not destination:
                logging.error(f"Aucune cible trouvée pour le package : {package}")
                continue
            futures.append(executor.submit(deliver_package, package, destination, access_token))

        # Attendre que toutes les tâches soient terminées
        for future in futures:
            future.result()


def main():
    # Dossier source (où se trouvent les dossiers à copier)
    source_dir = r"D:\handleFile\Depot"  # Remplacez par votre chemin source

    # Fichier de configuration JSON contenant le mapping des cibles
    config_file = r"D:\handleFile\config.json"  # Remplacez par votre chemin de configuration

    # Chargement du mapping des cibles
    mapping = load_mapping(config_file)
    if not mapping:
        logging.error("Le mapping des cibles est vide ou invalide.")
        return

    # Obtention du jeton d'accès
    access_token = get_access_token()
    if not access_token:
        logging.error("Impossible d'obtenir un jeton d'accès.")
        return

    # Préparation des colis
    packages = prepare_packages(source_dir)

    # Livraison des colis
    deliver_packages(packages, mapping, access_token)


if __name__ == "__main__":
    main()