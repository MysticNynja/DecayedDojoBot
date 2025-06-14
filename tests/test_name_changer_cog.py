import unittest
from unittest.mock import patch, MagicMock, AsyncMock

# Assuming cogs are importable. This might need sys.path adjustment if running tests directly
# from ..cogs.name_changer import name_changer_cog # This relative import might not work with `python -m unittest`
# For `python -m unittest discover`, direct imports from the project root should work if cogs is a package
from cogs.name_changer.name_changer_cog import NameChangerCog

class TestNameChangerCog(unittest.TestCase):
    def setUp(self):
        # Mock the bot object that the Cog's __init__ expects
        self.mock_bot = MagicMock()
        # If SERVER_ID and USER_ID are still read from os.getenv in cog's module scope,
        # we might need to patch os.getenv for those specific keys during test setup
        # For now, assuming they are handled or not critical for these unit tests' focus
        with patch('os.getenv', return_value="12345"): # Mocking env vars for cog init
             self.cog = NameChangerCog(self.mock_bot)

    @patch('aiohttp.ClientSession.get')
    async def test_get_random_male_name_success(self, mock_get):
        # Mock the response from the external API
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            "results": [{"name": {"first": "John"}}]
        }
        mock_response.raise_for_status = MagicMock() # Ensure it doesn't raise an error

        # Configure the mock_get context manager to return our mock_response
        mock_session_get_context_manager = AsyncMock()
        mock_session_get_context_manager.__aenter__.return_value = mock_response
        mock_get.return_value = mock_session_get_context_manager

        name = await self.cog.get_random_male_name()
        self.assertEqual(name, "John")

    @patch('aiohttp.ClientSession.get')
    async def test_get_random_male_name_api_failure(self, mock_get):
        mock_response = AsyncMock()
        mock_response.raise_for_status.side_effect = Exception("API Error")

        mock_session_get_context_manager = AsyncMock()
        mock_session_get_context_manager.__aenter__.return_value = mock_response
        mock_get.return_value = mock_session_get_context_manager

        name = await self.cog.get_random_male_name()
        self.assertIsNone(name)

    @patch('cogs.name_changer.name_changer_cog.NameChangerCog.get_random_male_name', new_callable=AsyncMock)
    async def test_perform_nickname_change_success(self, mock_get_name):
        mock_get_name.return_value = "TestName"

        mock_guild = MagicMock()
        mock_member = AsyncMock() # member.edit is async
        mock_guild.get_member.return_value = mock_member

        # Patch self.bot.get_guild that is used inside perform_nickname_change
        self.cog.bot.get_guild.return_value = mock_guild

        # SERVER_ID and USER_ID are accessed from module level in the cog
        # We need to ensure they are valid or patch them if they cause issues
        # For this test, assume they are 123 and 456 respectively
        with patch('cogs.name_changer.name_changer_cog.SERVER_ID', 123), \
             patch('cogs.name_changer.name_changer_cog.USER_ID', 456):
            success, message = await self.cog.perform_nickname_change(guild_id=123, target_user_id=456)

        self.assertTrue(success)
        self.assertEqual(message, "TestName")
        mock_member.edit.assert_called_once_with(nick="TestName")

    # More tests can be added for failure cases of perform_nickname_change
    # (e.g. guild not found, member not found, API fail for name, permission error)

if __name__ == '__main__':
    # This allows running the test file directly, but `python -m unittest discover` is preferred
    unittest.main()
