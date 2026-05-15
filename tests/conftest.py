from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_jwks_client():
    with patch("app.api.middleware.auth._jwks_client") as mock_client:
        mock_client.get_signing_key_from_jwt.return_value = MagicMock()
        yield mock_client


@pytest.fixture(autouse=True)
def mock_ensure_user_synced():
    # AuthMiddleware opens its own DB session to sync users on every authenticated
    # request; tests don't have a real DB and don't care about that path here.
    with patch("app.api.middleware.auth.ensure_user_synced") as mock:
        yield mock
