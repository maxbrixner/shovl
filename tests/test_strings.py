import pathlib
import unittest
from unittest.mock import MagicMock, patch

import shovl.services as services


class TestResolvePath(unittest.TestCase):
    @patch("shovl.services.strings.resolve_credentials")
    @patch("pathlib.Path.home")
    def test_resolve_home_path(
        self, mock_home: MagicMock, mock_resolve_credentials: MagicMock
    ) -> None:
        """
        Test that ~/ is correctly expanded to the home directory.
        """
        mock_home.return_value = pathlib.Path("/home/user")
        mock_resolve_credentials.side_effect = lambda x: x

        input_path = "~/configs/settings.json"
        expected = pathlib.Path("/home/user/configs/settings.json").resolve()

        result = services.resolve_path(input_path)

        self.assertEqual(result, expected)

        mock_resolve_credentials.assert_called_once_with(
            "~/configs/settings.json"
        )

    @patch("shovl.services.strings.resolve_credentials")
    def test_resolve_absolute_path(
        self, mock_resolve_credentials: MagicMock
    ) -> None:
        """
        Test that a standard absolute path is handled correctly.
        """
        mock_resolve_credentials.side_effect = lambda self: self

        input_path = "/etc/app/config.yaml"
        expected = pathlib.Path("/etc/app/config.yaml")

        result = services.resolve_path(input_path)

        self.assertEqual(result, expected)

    @patch("shovl.services.strings.resolve_credentials")
    def test_resolve_relative_path(
        self, mock_resolve_credentials: MagicMock
    ) -> None:
        """
        Test that a standard relative path is handled correctly.
        """
        mock_resolve_credentials.side_effect = lambda self: self

        input_path = "./../config.yaml"
        expected = pathlib.Path.cwd().parent / "config.yaml"

        result = services.resolve_path(input_path)
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
