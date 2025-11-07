import json
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error
import urllib.parse

# Configuration
MASTER_URL = "http://master:8000"
CHUNK_SIZE = 1024 * 1024  # 1MB

def upload_file(filename, content):
    """Upload a file to the GFS"""
    print(f"[CLIENT] Starting upload: {filename}")
    
    # Step 1: Request chunk allocation from Master
    try:
        data = json.dumps({
            "filename": filename,
            "filesize": len(content)
        }).encode()
        
        req = urllib.request.Request(
            f"{MASTER_URL}/allocate_chunks",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            allocation = json.loads(response.read().decode())
        
        print(f"[CLIENT] Received allocation for {len(allocation['allocations'])} chunks")
    
    except Exception as e:
        print(f"[CLIENT] Failed to get allocation: {e}")
        return False
    
    # Step 2: Upload chunks to assigned servers
    for alloc in allocation["allocations"]:
        chunk_id = alloc["chunk_id"]
        servers = alloc["servers"]
        index = alloc["index"]
        
        # Extract chunk data
        start = index * CHUNK_SIZE
        end = min(start + CHUNK_SIZE, len(content))
        chunk_data = content[start:end]
        
        # Upload to each replica server
        success = False
        for server_id in servers:
            try:
                # Determine server port
                port_map = {
                    "chunk_server_1": 9001,
                    "chunk_server_2": 9002,
                    "chunk_server_3": 9003
                }
                port = port_map.get(server_id, 9001)
                
                # Prepare upload data
                upload_data = f"chunk_id={chunk_id}&data={urllib.parse.quote(chunk_data)}".encode()
                
                req = urllib.request.Request(
                    f"http://{server_id}:{port}/upload",
                    data=upload_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    result = json.loads(response.read().decode())
                    print(f"[CLIENT] Uploaded {chunk_id} to {server_id}: {result}")
                    success = True
            
            except Exception as e:
                print(f"[CLIENT] Failed to upload {chunk_id} to {server_id}: {e}")
        
        # Register chunk with Master
        if success:
            try:
                data = json.dumps({
                    "filename": filename,
                    "chunk_id": chunk_id,
                    "servers": servers
                }).encode()
                
                req = urllib.request.Request(
                    f"{MASTER_URL}/register_chunk",
                    data=data,
                    headers={"Content-Type": "application/json"}
                )
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    result = json.loads(response.read().decode())
                    print(f"[CLIENT] Registered {chunk_id} with Master")
            
            except Exception as e:
                print(f"[CLIENT] Failed to register {chunk_id}: {e}")
        
        time.sleep(0.5)  # Simulate upload time
    
    print(f"[CLIENT] Upload completed: {filename}")
    return True

class ClientHandler(BaseHTTPRequestHandler):
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
            self._handle_upload_request()
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def _handle_upload_request(self):
        """Handle upload request from web UI"""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()
        
        try:
            data = json.loads(body)
            filename = data.get("filename", "test_file.txt")
            content = data.get("content", "Sample file content for testing GFS upload.")
            
            # Perform upload
            success = upload_file(filename, content)
            
            self._set_headers()
            self.wfile.write(json.dumps({
                "success": success,
                "filename": filename,
                "size": len(content)
            }).encode())
        
        except Exception as e:
            print(f"[CLIENT] Error: {e}")
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def main():
    # Start HTTP server for web UI requests
    server = HTTPServer(('0.0.0.0', 8001), ClientHandler)
    print("[CLIENT] Client service started on port 8001")
    server.serve_forever()

if __name__ == "__main__":
    main()