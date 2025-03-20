import msal
import time
import logging
from settings.config import app_id, client_secret, tenant_id, proxy, scopes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class TokenGenerator:
    def __init__(self, app_id, client_secret, tenant_id, proxy, scopes):
        self.app_id = app_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.proxy = proxy
        self.scopes = scopes
        self.token_response = None
        self.token_expiration_time = 0  # Temps d'expiration du token

        self.client = msal.ConfidentialClientApplication(
            client_id=self.app_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            proxies={'http': self.proxy, 'https': self.proxy}
        )

    def is_token_expired(self):
        """Vérifie si le token est expiré."""
        return time.time() >= self.token_expiration_time

    def generate_access_token(self):
        """Génère un nouveau token d'accès."""
        self.token_response = self.client.acquire_token_for_client(scopes=self.scopes)
        if 'access_token' not in self.token_response:
            raise Exception("Failed to obtain access token")

        # Mettre à jour le temps d'expiration du token
        self.token_expiration_time = time.time() + self.token_response.get('expires_in',
                                                                           3600) - 300  # 5 minutes de marge
        logging.info("New access token generated.")
        return self.token_response

    def get_valid_token(self):
        """Renvoie un token valide, en le renouvelant si nécessaire."""
        if self.is_token_expired() or not self.token_response:
            self.generate_access_token()
        return self.token_response['access_token']