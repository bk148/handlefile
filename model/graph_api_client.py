import requests
import logging

class GraphAPIClient:
    def __init__(self, token_generator, proxy):
        self.token_generator = token_generator
        self.proxy = proxy
        self.headers = {'Authorization': f'Bearer {self.token_generator.generate_access_token()["access_token"]}'}
        self.proxies = {'http': self.proxy, 'https': self.proxy}
        self.logger = logging.getLogger(__name__)

    def get(self, url):
        """Effectue une requête GET vers l'API Graph."""
        try:
            response = requests.get(url, headers=self.headers, proxies=self.proxies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"GET request failed: {e}")
            raise

    def post(self, url, data):
        """Effectue une requête POST vers l'API Graph."""
        try:
            response = requests.post(url, headers=self.headers, json=data, proxies=self.proxies)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"POST request failed: {e}")
            raise

    def put(self, url, data):
        """Effectue une requête PUT vers l'API Graph."""
        try:
            response = requests.put(url, headers=self.headers, data=data, proxies=self.proxies)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"PUT request failed: {e}")
            raise