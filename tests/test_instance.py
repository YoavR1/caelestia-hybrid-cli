"""The shell-instance selector.

These exist because the bug they guard against is invisible at runtime: pointing
the CLI at the wrong Quickshell config does not raise, it just talks to a
different process. A test is the only place that mistake is loud.
"""

import subprocess
import sys
import unittest
from unittest import mock

from caelestia.utils import instance


class SelectorTest(unittest.TestCase):
    def test_defaults_to_the_caelestia_config(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(instance.selector(), ["-c", "caelestia"])

    def test_config_name_is_overridable(self) -> None:
        with mock.patch.dict("os.environ", {"CAELESTIA_SHELL_CONFIG": "hybrid"}, clear=True):
            self.assertEqual(instance.selector(), ["-c", "hybrid"])

    def test_a_path_wins_over_a_config_name(self) -> None:
        env = {"CAELESTIA_SHELL_PATH": "/home/u/shell", "CAELESTIA_SHELL_CONFIG": "hybrid"}
        with mock.patch.dict("os.environ", env, clear=True):
            self.assertEqual(instance.selector(), ["-p", "/home/u/shell"])

    def test_an_empty_config_name_falls_back_rather_than_selecting_nothing(self) -> None:
        # `-c ""` would be a silently broken selector, so empty must mean unset.
        with mock.patch.dict("os.environ", {"CAELESTIA_SHELL_CONFIG": ""}, clear=True):
            self.assertEqual(instance.selector(), ["-c", "caelestia"])

    def test_an_empty_path_falls_back_too(self) -> None:
        with mock.patch.dict("os.environ", {"CAELESTIA_SHELL_PATH": ""}, clear=True):
            self.assertEqual(instance.selector(), ["-c", "caelestia"])


class CommandTest(unittest.TestCase):
    def test_qs_builds_a_full_command_line(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(instance.qs("-n"), ["qs", "-c", "caelestia", "-n"])

    def test_ipc_targets_the_selected_instance(self) -> None:
        with mock.patch.dict("os.environ", {"CAELESTIA_SHELL_PATH": "/tmp/s"}, clear=True):
            self.assertEqual(
                instance.ipc("nexus", "open"),
                ["qs", "-p", "/tmp/s", "ipc", "call", "nexus", "open"],
            )

    def test_describe_names_what_is_addressed(self) -> None:
        with mock.patch.dict("os.environ", {"CAELESTIA_SHELL_PATH": "/tmp/s"}, clear=True):
            self.assertIn("/tmp/s", instance.describe())
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertIn("caelestia", instance.describe())


class CallSiteTest(unittest.TestCase):
    """No subcommand may spell out the selector itself again."""

    def test_no_hardcoded_config_name_outside_this_module(self) -> None:
        out = subprocess.run(
            [
                "git", "grep", "-n", '"-c", "caelestia"', "--",
                "src/caelestia/subcommands", "src/caelestia/utils",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(out.stdout.strip(), "", f"hardcoded instance selector:\n{out.stdout}")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
