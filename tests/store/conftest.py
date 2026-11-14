import sqlite3

import pytest


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    terminalreporter.write_line(
        f"store: sqlite3.sqlite_version={sqlite3.sqlite_version} "
        f"sqlite3.threadsafety={sqlite3.threadsafety}"
    )
