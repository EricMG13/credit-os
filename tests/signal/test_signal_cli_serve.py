"""S-14: ``serve`` through ``main``. A real server on 127.0.0.1 port 0, stopped by the service's
own ``shutdown`` from one helper thread; no name is resolved (a non-ASCII name whose encoding
fails stands for a host that cannot be listened on)."""

import contextlib
import io
import logging
import re
import sys
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest
from service_support import lingering_connection

from credit_os.signal import cli, service

BAD_HOST = "é" * 64 + ".lan"


def serve_main(root: Path, *args: str) -> tuple[int, str]:
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        code = cli.main(["--root", str(root), "serve", *args])
    return code, err.getvalue()


def test_wildcard_host_is_refused(tmp_path: Path) -> None:
    assert serve_main(tmp_path, "--host", "0.0.0.0", "--port", "0") == (
        2,
        service.WILDCARD_MESSAGE + "\n",
    )
    assert not (tmp_path / "signal").exists()


def test_a_host_that_cannot_be_encoded_exits_2_with_one_line(tmp_path: Path) -> None:
    with pytest.raises(UnicodeError):
        BAD_HOST.encode("idna")
    code, err = serve_main(tmp_path, "--host", BAD_HOST, "--port", "0")
    assert code == 2
    assert err.startswith(f"cannot listen on {BAD_HOST}:0: ") and err.count("\n") == 1


def test_a_port_out_of_range_exits_2(tmp_path: Path) -> None:
    assert serve_main(tmp_path, "--port", "70000") == (2, "--port must be from 0 to 65535\n")


def test_serve_answers_on_loopback_and_returns_promptly_after_shutdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[ThreadingHTTPServer] = []
    real = service.make_server

    def spy(root: Path, host: str, port: int, *, loop: service.Loop | None = None) -> Any:
        server = real(root, host, port, loop=loop)  # the real server, remembered
        started.append(server)
        return server

    monkeypatch.setattr(service, "make_server", spy)
    seen: list[tuple[int, bytes]] = []

    def client() -> None:
        deadline = time.monotonic() + 10
        while not started and time.monotonic() < deadline:
            time.sleep(0.01)
        server = started[0]
        port = server.server_address[1]
        connection = lingering_connection(port, 10)
        connection.request("GET", "/api/me", headers={"Host": f"127.0.0.1:{port}"})
        response = connection.getresponse()
        seen.append((response.status, response.read()))
        connection.close()
        server.shutdown()

    helper = threading.Thread(target=client, daemon=True)
    helper.start()
    began = time.monotonic()
    code, err = serve_main(tmp_path, "--port", "0")
    helper.join(timeout=10)
    assert code == 0 and time.monotonic() - began < 8
    assert seen == [(200, b'{"name": null}')]
    assert err.startswith("serving http://127.0.0.1:")


def test_main_configures_logging_once_at_info_to_stderr(tmp_path: Path) -> None:
    root = logging.getLogger()
    saved, level = root.handlers[:], root.level
    root.handlers.clear()
    try:
        run_twice = [cli.main(["--root", str(tmp_path), "stories"]) for _ in range(2)]
        assert run_twice == [0, 0]
        assert len(root.handlers) == 1 and root.level == logging.INFO
        handler = root.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stderr
        record = logging.LogRecord("x", logging.INFO, "f", 1, "one %s", ("line",), None)
        assert re.fullmatch(
            r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d{3} INFO x one line", handler.format(record)
        )
    finally:
        root.handlers[:] = saved
        root.setLevel(level)
