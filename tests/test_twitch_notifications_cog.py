import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import time # For testing token expiry
import os

# For `python -m unittest discover`, direct imports from the project root should work
from cogs.twitch_notifications.twitch_notifications_cog import TwitchNotificationsCog

# Mock os.getenv for TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET at the module level for the cog
@patch.dict(os.environ, {"TWITCH_CLIENT_ID": "test_client_id", "TWITCH_CLIENT_SECRET": "test_client_secret"})
class TestTwitchNotificationsCog(unittest.IsolatedAsyncioTestCase): # Using IsolatedAsyncioTestCase for async tests

    def setUp(self):
        self.mock_bot = MagicMock()
        # Patch _load_json_data to avoid file I/O during tests
        with patch('cogs.twitch_notifications.twitch_notifications_cog._load_json_data', return_value={}) as mock_load_json:
            self.cog = TwitchNotificationsCog(self.mock_bot)
            self.mock_load_json = mock_load_json


    @patch('aiohttp.ClientSession.post')
    async def test_get_twitch_app_access_token_success(self, mock_post):
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "access_token": "test_token",
            "expires_in": 3600
        }
        mock_response.raise_for_status = MagicMock()

        mock_session_post_context_manager = AsyncMock()
        mock_session_post_context_manager.__aenter__.return_value = mock_response
        mock_post.return_value = mock_session_post_context_manager

        token = await self.cog.get_twitch_app_access_token()
        self.assertEqual(token, "test_token")
        self.assertEqual(self.cog.twitch_access_token, "test_token")
        self.assertGreater(self.cog.twitch_token_expires_at, time.time())

    @patch('aiohttp.ClientSession.post')
    async def test_get_twitch_app_access_token_uses_cached_token(self, mock_post):
        self.cog.twitch_access_token = "cached_test_token"
        self.cog.twitch_token_expires_at = time.time() + 3600 # Token is valid

        token = await self.cog.get_twitch_app_access_token()
        self.assertEqual(token, "cached_test_token")
        mock_post.assert_not_called() # Should not make a new request

    @patch('aiohttp.ClientSession.post')
    async def test_get_twitch_app_access_token_refresh_expired(self, mock_post):
        self.cog.twitch_access_token = "expired_token"
        self.cog.twitch_token_expires_at = time.time() - 10 # Token is expired

        new_mock_response = AsyncMock()
        new_mock_response.json.return_value = {"access_token": "new_fresh_token", "expires_in": 3600}
        new_mock_response.raise_for_status = MagicMock()

        mock_session_post_context_manager = AsyncMock()
        mock_session_post_context_manager.__aenter__.return_value = new_mock_response
        mock_post.return_value = mock_session_post_context_manager

        token = await self.cog.get_twitch_app_access_token()
        self.assertEqual(token, "new_fresh_token")
        mock_post.assert_called_once()


    @patch('aiohttp.ClientSession.get')
    @patch('cogs.twitch_notifications.twitch_notifications_cog.TwitchNotificationsCog.get_twitch_app_access_token', new_callable=AsyncMock)
    async def test_get_twitch_user_info_success(self, mock_get_token, mock_aio_get):
        mock_get_token.return_value = "fake_access_token"

        mock_api_response = AsyncMock()
        mock_api_response.json.return_value = {
            "data": [{
                "id": "12345",
                "login": "testuser",
                "display_name": "TestUser"
            }]
        }
        mock_api_response.raise_for_status = MagicMock()

        mock_session_get_context_manager = AsyncMock()
        mock_session_get_context_manager.__aenter__.return_value = mock_api_response
        mock_aio_get.return_value = mock_session_get_context_manager

        user_info = await self.cog.get_twitch_user_info("testuser")
        self.assertIsNotNone(user_info)
        if user_info is not None:
            self.assertEqual(user_info["id"], "12345")
            self.assertEqual(user_info["login"], "testuser")

    @patch('cogs.twitch_notifications.twitch_notifications_cog.TwitchNotificationsCog.get_twitch_app_access_token', new_callable=AsyncMock)
    async def test_get_twitch_user_info_no_token(self, mock_get_token):
        mock_get_token.return_value = None # Simulate token fetch failure
        user_info = await self.cog.get_twitch_user_info("testuser")
        self.assertIsNone(user_info)

    # Similar tests can be written for get_twitch_user_profile, get_game_info, get_stream_clips
    # by mocking aiohttp.ClientSession.get and the responses.

    # Testing the main task check_twitch_streams_task is complex.
    # It would involve mocking bot.get_channel, channel.fetch_message, channel.send,
    # multiple API call helpers, and time progression.
    # For now, focusing on testable units like the API helpers.

if __name__ == '__main__':
    unittest.main()
