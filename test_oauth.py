import unittest
from unittest.mock import patch, mock_open, MagicMock
import youtube_mass_updater as ymu

class TestOAuth(unittest.TestCase):

    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="mocked_data")
    @patch('pickle.load')
    @patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file')
    @patch('youtube_mass_updater.build')
    def test_authenticate_with_existing_token(self, mock_build, mock_flow, mock_pickle_load, mock_open, mock_exists):
        # Simuler le fait que token.pickle existe
        mock_exists.return_value = True

        # Simuler le chargement des données depuis token.pickle
        mock_credentials = MagicMock()
        mock_credentials.valid = True
        mock_pickle_load.return_value = mock_credentials

        # Simuler la réponse de la fonction build
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Appeler la fonction
        client = ymu.authenticate_with_oauth()

        # Vérifications
        mock_exists.assert_called_once_with('token.pickle')
        mock_open.assert_called_once_with('token.pickle', 'rb')
        mock_pickle_load.assert_called_once()
        mock_flow.assert_not_called()  # Le flux OAuth ne devrait pas être appelé si le token est valide
        mock_build.assert_called_once_with('youtube', 'v3', credentials=mock_credentials)

if __name__ == "__main__":
    unittest.main(exit=False)
