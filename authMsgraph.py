import msal
import time
from settings.config import app_id, client_secret, tenant_id, proxy, scopes

class TokenGenerator:
    def __init__(self, app_id, client_secret, tenant_id, proxy, scopes):
        self.app_id = app_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.proxy = proxy
        self.scopes = scopes
        self.client = msal.ConfidentialClientApplication(
            client_id=self.app_id,
            client_credential=self.client_secret,
            authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            proxies={
                'http': self.proxy,
                'https': self.proxy
            }
        )
        self.token_response = None

    def generate_access_token(self):
        self.token_response = self.client.acquire_token_silent(self.scopes, account=None)
        if self.token_response and 'expires_in' in self.token_response:
            expiration_time = self.token_response['expires_in']
            current_time = time.time()
            if expiration_time - current_time < 300:
                self.token_response = None
        if not self.token_response:
            self.token_response = self.client.acquire_token_for_client(scopes=self.scopes)
        if 'access_token' not in self.token_response:
            raise Exception("Failed to obtain access token")
        return self.token_response