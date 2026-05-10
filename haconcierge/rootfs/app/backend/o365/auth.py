import logging
import msal

logger = logging.getLogger(__name__)

GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]


class O365Auth:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str):
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._app = None
        self._token_cache = None

    def _get_app(self) -> msal.ConfidentialClientApplication:
        if not self._app:
            authority = f"https://login.microsoftonline.com/{self.tenant_id}"
            self._app = msal.ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=authority,
            )
        return self._app

    def get_token(self) -> str | None:
        app = self._get_app()
        result = app.acquire_token_silent(GRAPH_SCOPES, account=None)
        if not result:
            result = app.acquire_token_for_client(scopes=GRAPH_SCOPES)
        if "access_token" in result:
            return result["access_token"]
        logger.error("O365 auth failed: %s", result.get("error_description", "unknown"))
        return None

    def is_configured(self, tenant_id, client_id, client_secret) -> bool:
        return all([tenant_id, client_id, client_secret])
