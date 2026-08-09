from __future__ import annotations

import threading

from paulsha_cortex.monitor.transport import (
    bind_monitor_listener,
    connect_monitor_socket,
    remove_monitor_endpoint,
)


def test_monitor_transport_round_trip_on_current_platform(tmp_path):
    endpoint = tmp_path / "monitor.sock"
    listener = bind_monitor_listener(endpoint)

    def serve_once():
        connection, _ = listener.accept()
        with connection:
            connection.sendall(connection.recv(4))

    thread = threading.Thread(target=serve_once)
    thread.start()
    with connect_monitor_socket(endpoint, timeout=2.0) as client:
        client.sendall(b"ping")
        assert client.recv(4) == b"ping"
    thread.join(timeout=2.0)
    listener.close()
    remove_monitor_endpoint(endpoint)
    assert not endpoint.exists()
