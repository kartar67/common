#!/usr/bin/env python3
import http.server
import socketserver
import os

# Set the port to serve on
PORT = 12000

# Set the directory to serve files from
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'X-Requested-With, Content-Type, Accept')
        super().end_headers()

    def do_OPTIONS(self):
        # Handle OPTIONS requests for CORS preflight
        self.send_response(200)
        self.end_headers()

# Change to the directory containing the files
os.chdir(DIRECTORY)

# Create the server
Handler = CORSHTTPRequestHandler
httpd = socketserver.TCPServer(("0.0.0.0", PORT), Handler)

print(f"Serving at port {PORT}")
print(f"Open https://work-1-ykzgrxwjkqvqgmtj.prod-runtime.all-hands.dev in your browser")
httpd.serve_forever()