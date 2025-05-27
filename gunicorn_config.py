############################################
#
#   gunicorn_config.py
#
############################################
import os
import socket
import threading
import time
#from app import app
import app

def start_unix_socket_server(path):
    # Remove the socket file if it already exists
    if os.path.exists(path):
        os.remove(path)

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
        server.bind(path)
        server.listen()
        print(f"[Unix Server] Listening on {path}")
        while True:
            conn, _ = server.accept()
            with conn:
                data = conn.recv(1024)
                if data:
                    print(f"[Unix Server] Received: {data.decode()}")
                    conn.sendall(b"Echo: " + data)

def post_fork(server, worker):
    pid = worker.pid
#    sock_path = f"/tmp/worker_{pid}.sock"
    sock_path = "/tmp/gw_socket"

    # Start the Unix socket server
    thread = threading.Thread(target=start_unix_socket_server, args=(sock_path,), daemon=True)
    thread.start()
    print(f"[Gunicorn] Started Unix socket server at {sock_path} in worker {pid}")

    # Wait for the socket server to be ready, then connect
    time.sleep(1)
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(sock_path)
        app.unix_client = client
        print(f"[Gunicorn] Connected Flask app to Unix socket at {sock_path}")
    except Exception as e:
        print(f"[Gunicorn] Failed to connect to Unix socket server: {e}")
