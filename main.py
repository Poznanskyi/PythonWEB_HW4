from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from urllib.parse import unquote_plus, urlparse
import os
import socket
import json
from pathlib import Path
from datetime import datetime
import mimetypes

UDP_IP = '127.0.0.1'
UDP_PORT = 5000

STORAGE_DIR = Path().joinpath('storage')
FILE_STORAGE = STORAGE_DIR / 'data.json'


def run_socket():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        print("Running socket...")
        s.bind((UDP_IP, UDP_PORT))
        try:
            while True:
                data = s.recv(1024)
                if data:
                    save_data_to_json(data)
        except KeyboardInterrupt:
            print(f'Destroy server')
        finally:
            s.close()


def save_data_to_json(data):
    with open(FILE_STORAGE, 'r') as f:
        messages = json.load(f)

    message = json.loads(data.decode())
    messages.update({str(datetime.now()): message})

    with open('storage/data.json', 'w') as f:
        json.dump(messages, f, indent=4)


class HttpHandler(BaseHTTPRequestHandler):
    source_path = 'front-init'

    def do_POST(self):
        pr_url = urlparse(self.path)

        data: bytes = self.rfile.readline(int(self.headers['Content-Length']))
        query_data: str = unquote_plus(data.decode())

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((UDP_IP, UDP_PORT))
            data_dict = {key: value for key, value in [
                el.split('=') for el in query_data.split('&')]}
            s.sendall(json.dumps(data_dict).encode())

        if pr_url.path == '/message':
            self.send_response(302)
            self.send_header('Location', '/message')
        self.end_headers()

    def do_GET(self):
        pr_url = urlparse(self.path)

        if pr_url.path == '/':
            self.send_html_file(self.source_path + '/index.html')
        elif pr_url.path == '/message':
            self.send_html_file(self.source_path + '/message.html')
        elif os.path.exists(self.source_path + pr_url.path):
            self.send_static(self.source_path + pr_url.path)
        else:
            self.send_html_file(self.source_path + '/error.html', 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as fd:
            self.wfile.write(fd.read())

    def send_static(self, filename, status=200):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", 'text/plain')
        self.end_headers()
        with open(f'{filename}', 'rb') as file:
            self.wfile.write(file.read())


def run_http_server(server_class=HTTPServer, handler_class=HttpHandler):
    print("Running server...")
    server_address = ('', 3000)
    http = server_class(server_address, handler_class)
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


def main():
    STORAGE_DIR.mkdir(exist_ok=True)
    if not FILE_STORAGE.exists():
        with open(FILE_STORAGE, 'w') as f:
            json.dump({}, f)
    server_thread = Thread(target=run_http_server)
    server_thread.start()
    socket_thread = Thread(target=run_socket)
    socket_thread.start()


if __name__ == '__main__':
    exit(main())
