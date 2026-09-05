"""Locating the shell instance this CLI should talk to.

Every subcommand that reaches the shell used to spell out ``qs -c caelestia``.
``-c`` resolves a Quickshell config *by name*, searching each XDG config
directory for ``quickshell/<name>/shell.qml``. That is fine on a machine with
exactly one Caelestia installed, and wrong on every other kind.

Concretely: with a packaged shell in ``/etc/xdg/quickshell/caelestia`` and a
checkout being run as ``qs -p ~/my-shell``, the name resolves to the package.
Every CLI subcommand then drives a different process from the one on screen,
and reports nothing unusual while doing it -- ``execDetached`` has no failure
to report, and an IPC call to a config with no running instance simply says so
and exits. The shell's launcher had a Settings action that failed this way for
weeks, and the fault was invisible until someone listed the running processes.

Resolution order, first match wins:

1. ``$CAELESTIA_SHELL_PATH`` -- a config directory or ``shell.qml``, passed to
   ``qs -p``. This is what a checkout wants; ``direnv`` can export it next to
   ``QML2_IMPORT_PATH`` so the CLI and the shell always agree.
2. ``$CAELESTIA_SHELL_CONFIG`` -- a config *name*, passed to ``qs -c``, for
   people running more than one named config.
3. ``caelestia`` -- the historical default, unchanged for existing installs.
"""

import os
import subprocess

DEFAULT_CONFIG = "caelestia"


def selector() -> list[str]:
    """Return the ``qs`` flags that select the shell instance."""
    path = os.environ.get("CAELESTIA_SHELL_PATH")
    if path:
        return ["-p", path]

    return ["-c", os.environ.get("CAELESTIA_SHELL_CONFIG") or DEFAULT_CONFIG]


def qs(*args: str) -> list[str]:
    """Return a full ``qs`` command line addressing the shell."""
    return ["qs", *selector(), *args]


def ipc(*args: str) -> list[str]:
    """Return a full ``qs ... ipc call ...`` command line."""
    return qs("ipc", "call", *args)


def describe() -> str:
    """Human-readable description of the instance being addressed."""
    flag, value = selector()
    return f"path {value}" if flag == "-p" else f"config {value!r}"


def run(*args: str) -> str:
    """Run a ``qs`` command against the shell, failing with a legible message.

    ``subprocess.check_output`` raises ``CalledProcessError``, and nothing up the
    stack catches it, so the previous behaviour for the ordinary case of "the
    shell is not running" was a Python traceback ending in ``exit status 255``.
    That is the same information as "no running instances", spelled so it reads
    like a bug in the CLI.
    """
    try:
        return subprocess.check_output(qs(*args), text=True, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        raise SystemExit("qs (quickshell) is not installed, or is not on PATH") from None
    except subprocess.CalledProcessError as e:
        detail = (e.output or "").strip().splitlines()
        first = next((line for line in detail if line.strip()), "")
        raise SystemExit(
            f"could not reach the shell at {describe()}"
            + (f": {first}" if first else "")
            + "\n\nSet CAELESTIA_SHELL_PATH to a checkout, or CAELESTIA_SHELL_CONFIG to a"
            "\nconfig name, if the shell is running somewhere other than the default."
        ) from None
