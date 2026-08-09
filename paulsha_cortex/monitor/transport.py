"""Local monitor transport with Unix-socket and native Windows backends."""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from uuid import uuid4

from paulsha_cortex.lib.durability import fsync_directory

ENDPOINT_SCHEMA = "cortex-monitor-tcp/v1"
LOOPBACK_HOST = "127.0.0.1"


def uses_unix_socket() -> bool:
    return hasattr(socket, "AF_UNIX")


def _write_tcp_endpoint(path: Path, *, port: int) -> None:
    payload = {
        "schema": ENDPOINT_SCHEMA,
        "host": LOOPBACK_HOST,
        "port": port,
    }
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def _read_tcp_endpoint(path: Path) -> tuple[str, int]:
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("monitor TCP endpoint must be a regular file")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("monitor TCP endpoint is invalid") from error
    if not isinstance(payload, dict) or payload.get("schema") != ENDPOINT_SCHEMA:
        raise ValueError("monitor TCP endpoint schema is invalid")
    host = payload.get("host")
    port = payload.get("port")
    if host != LOOPBACK_HOST or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("monitor TCP endpoint address is invalid")
    return host, port


def bind_monitor_listener(path: str | Path, *, backlog: int = 16) -> socket.socket:
    endpoint = Path(path)
    endpoint.parent.mkdir(parents=True, exist_ok=True)
    if uses_unix_socket():
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            previous_umask = os.umask(0o177)
            try:
                listener.bind(str(endpoint))
            finally:
                os.umask(previous_umask)
            os.chmod(endpoint, 0o600)
            listener.listen(backlog)
            return listener
        except BaseException:
            listener.close()
            raise

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.bind((LOOPBACK_HOST, 0))
        listener.listen(backlog)
        _host, port = listener.getsockname()
        _write_tcp_endpoint(endpoint, port=int(port))
        return listener
    except BaseException:
        listener.close()
        raise


def connect_monitor_socket(
    path: str | Path, *, timeout: float | None = None
) -> socket.socket:
    endpoint = Path(path)
    if uses_unix_socket():
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client.settimeout(timeout)
            client.connect(str(endpoint))
            return client
        except BaseException:
            client.close()
            raise

    host, port = _read_tcp_endpoint(endpoint)
    return socket.create_connection((host, port), timeout=timeout)


def tcp_monitor_endpoint_has_owner(path: str | Path) -> bool:
    """Return whether a Windows endpoint port is still exclusively owned."""
    host, port = _read_tcp_endpoint(Path(path))
    exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
    if exclusive is None:
        return True
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.setsockopt(socket.SOL_SOCKET, exclusive, 1)
        try:
            probe.bind((host, port))
        except OSError:
            return True
        return False
    finally:
        probe.close()


def remove_monitor_endpoint(path: str | Path) -> None:
    Path(path).unlink(missing_ok=True)
