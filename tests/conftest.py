from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def mock_jwks_client():
    with patch("app.api.middleware.auth._jwks_client") as mock_client:
        mock_client.get_signing_key_from_jwt.return_value = MagicMock()
        yield mock_client
