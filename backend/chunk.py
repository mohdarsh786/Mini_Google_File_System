import json
import os
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error

# Configuration
MASTER_URL = "http://master:8000"
HEARTBEAT_INTERVAL = 5  # seconds
DATA_DIR = "/data/chunks"

# Server identity
SERVER_ID = os.environ.get("SERVER_ID", "chunk_server_1")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "9001"))

# Initialize storage
os.makedirs(DATA_DIR, exist_ok=True)

def send_heartbeat():
    """Send periodic heartbeat to master"""
    while True:
        try:
            data = json.dumps({
                "server_id": SERVER_ID,
                "host": SERVER_ID,
                "port": SERVER_PORT
            }).encode()
            
            req = urllib.request.Request(
                f"{MASTER_URL}/heartbeat",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode())
                print(f"[{SERVER_ID}] Heartbeat sent: {result}")
        
        except Exception as e:
            print(f"[{SERVER_ID}] Heartbeat failed: {e}")
        
        time.sleep(HEARTBEAT_INTERVAL)

class ChunkServerHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_headers()
    
    def do_POST(self):
        if self.path == "/upload":
            self._handle_upload()
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_GET(self):
        if self.path.startswith("/download/"):
            self._handle_download()
        elif self.path == "/health":
            self._handle_health()
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def _handle_upload(self):
        """Handle chunk upload"""
        content_length = int(self.headers.get('Content-Length', 0))
        
        # Read multipart form data
        body = self.rfile.read(content_length)
        
        # Parse simple format: chunk_id=xxx&data=yyy
        try:
            parts = body.decode().split('&')
            chunk_id = None
            chunk_data = None
            
            for part in parts:
                if '=' in part:
                    key, value = part.split('=', 1)
                    if key == 'chunk_id':
                        chunk_id = value
                    elif key == 'data':
                        chunk_data = value
            
            if not chunk_id:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Missing chunk_id"}).encode())
                return
            
            # Save chunk to disk
            chunk_path = os.path.join(DATA_DIR, chunk_id)
            with open(chunk_path, 'w') as f:
                f.write(chunk_data or "")
            
            print(f"[{SERVER_ID}] Stored chunk: {chunk_id}")
            
            self._set_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "chunk_id": chunk_id,
                "server_id": SERVER_ID
            }).encode())
        
        except Exception as e:
            print(f"[{SERVER_ID}] Upload error: {e}")
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def _handle_download(self):
        """Handle chunk download"""
        chunk_id = self.path.split('/')[-1]
        chunk_path = os.path.join(DATA_DIR, chunk_id)
        
        if not os.path.exists(chunk_path):
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Chunk not found"}).encode())
            return
        
        with open(chunk_path, 'r') as f:
            data = f.read()
        
        self._set_headers()
        self.wfile.write(json.dumps({
            "chunk_id": chunk_id,
            "data": data
        }).encode())
    
    def _handle_health(self):
        """Health check endpoint"""
        chunks = os.listdir(DATA_DIR)
        
        self._set_headers()
        self.wfile.write(json.dumps({
            "server_id": SERVER_ID,
            "status": "active",
            "chunks_stored": len(chunks)
        }).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def main():
    # Start heartbeat thread
    threading.Thread(target=send_heartbeat, daemon=True).start()
    
    # Start HTTP server
    server = HTTPServer(('0.0.0.0', SERVER_PORT), ChunkServerHandler)
    print(f"[{SERVER_ID}] Chunk Server started on port {SERVER_PORT}")
    server.serve_forever()

if __name__ == "__main__":
    main()