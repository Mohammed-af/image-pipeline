#!/usr/bin/env python3
from http.server import HTTPServer, SimpleHTTPRequestHandler

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def run(port=8083):
    server_address = ('', port)
    httpd = HTTPServer(server_address, CORSRequestHandler)
    print(f"HTML GUI running at http://localhost:{port}/search.html")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
