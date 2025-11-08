import json
import os
import time
import threading
import hashlib
import secrets
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

# Configuration
HEARTBEAT_TIMEOUT = 15  # seconds
REPLICATION_FACTOR = 2
CHUNK_SIZE = 1024 * 1024  # 1MB
DATA_DIR = "/data/master"
METADATA_FILE = f"{DATA_DIR}/chunks.json"
USERS_FILE = f"{DATA_DIR}/users.json"
SESSIONS_FILE = f"{DATA_DIR}/sessions.json"

# Global state
chunk_servers = {}
metadata = {"files": {}, "chunks": {}}
users = {}
sessions = {}  # Store active sessions
heartbeat_lock = threading.Lock()
metadata_lock = threading.Lock()
session_lock = threading.Lock()

# Initialize data directory
os.makedirs(DATA_DIR, exist_ok=True)

def load_data():
    """Load metadata, users, and sessions from disk"""
    global metadata, users, sessions
    
    # Load metadata
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)
    
    # Load users or create defaults
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            users = json.load(f)
    else:
        users = {
            "admin": {
                "password": hashlib.sha256("admin123".encode()).hexdigest(),
                "role": "admin",
                "created_by": "system"
            }
        }
        save_users()
    
    # Load sessions
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE, 'r') as f:
            sessions = json.load(f)
        # Clean expired sessions
        clean_expired_sessions()

def save_metadata():
    """Save metadata to disk"""
    with metadata_lock:
        with open(METADATA_FILE, 'w') as f:
            json.dump(metadata, f, indent=2)

def save_users():
    """Save users to disk"""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def save_sessions():
    """Save sessions to disk"""
    with session_lock:
        with open(SESSIONS_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)

def create_session(username, role):
    """Create a new session token"""
    token = secrets.token_urlsafe(32)
    expiry = (datetime.now() + timedelta(hours=24)).isoformat()
    
    with session_lock:
        sessions[token] = {
            "username": username,
            "role": role,
            "expiry": expiry
        }
        save_sessions()
    
    return token

def validate_session(token):
    """Validate session token"""
    with session_lock:
        if token not in sessions:
            return None
        
        session = sessions[token]
        expiry = datetime.fromisoformat(session["expiry"])
        
        if datetime.now() > expiry:
            del sessions[token]
            save_sessions()
            return None
        
        return session

def clean_expired_sessions():
    """Remove expired sessions"""
    with session_lock:
        now = datetime.now()
        expired = [token for token, session in sessions.items()
                  if datetime.fromisoformat(session["expiry"]) < now]
        
        for token in expired:
            del sessions[token]
        
        if expired:
            save_sessions()

def register_chunk_server(server_id, host, port):
    """Register or update a chunk server"""
    with heartbeat_lock:
        chunk_servers[server_id] = {
            "host": host,
            "port": port,
            "last_heartbeat": time.time(),
            "status": "active"
        }
    print(f"[MASTER] Registered chunk server: {server_id}")

def check_heartbeats():
    """Monitor chunk server heartbeats and detect failures"""
    while True:
        time.sleep(5)
        current_time = time.time()
        
        with heartbeat_lock:
            for server_id, info in chunk_servers.items():
                if info["status"] == "active":
                    if current_time - info["last_heartbeat"] > HEARTBEAT_TIMEOUT:
                        info["status"] = "failed"
                        print(f"[MASTER] Server {server_id} marked as FAILED")
                        threading.Thread(target=re_replicate_chunks, args=(server_id,), daemon=True).start()
        
        # Clean expired sessions periodically
        clean_expired_sessions()

def re_replicate_chunks(failed_server):
    """Re-replicate chunks from a failed server"""
    print(f"[MASTER] Starting re-replication for failed server: {failed_server}")
    
    with metadata_lock:
        active_servers = [sid for sid, info in chunk_servers.items() 
                         if info["status"] == "active"]
        
        if not active_servers:
            print("[MASTER] No active servers for re-replication!")
            return
        
        # Find chunks on failed server
        for chunk_id, chunk_info in metadata["chunks"].items():
            if failed_server in chunk_info["servers"]:
                # Remove failed server
                chunk_info["servers"].remove(failed_server)
                
                # Add to new server if below replication factor
                if len(chunk_info["servers"]) < REPLICATION_FACTOR:
                    new_server = active_servers[hash(chunk_id) % len(active_servers)]
                    if new_server not in chunk_info["servers"]:
                        chunk_info["servers"].append(new_server)
                        print(f"[MASTER] Re-replicating {chunk_id} to {new_server}")
        
        save_metadata()

class MasterHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/status":
            self._handle_status()
        elif path == "/users":
            self._handle_get_users()
        elif path == "/logs":
            self._handle_logs()
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else "{}"
        
        try:
            data = json.loads(body)
        except:
            data = {}
        
        if path == "/heartbeat":
            self._handle_heartbeat(data)
        elif path == "/login":
            self._handle_login(data)
        elif path == "/logout":
            self._handle_logout(data)
        elif path == "/signup":
            self._handle_signup(data)
        elif path == "/create_user":
            self._handle_create_user(data)
        elif path == "/promote_user":
            self._handle_promote_user(data)
        elif path == "/allocate_chunks":
            self._handle_allocate_chunks(data)
        elif path == "/register_chunk":
            self._handle_register_chunk(data)
        elif path == "/simulate_failure":
            self._handle_simulate_failure(data)
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def _handle_status(self):
        """Return system status"""
        with heartbeat_lock:
            servers_status = {sid: {
                "status": info["status"],
                "last_heartbeat": info["last_heartbeat"],
                "host": info["host"],
                "port": info["port"]
            } for sid, info in chunk_servers.items()}
        
        with metadata_lock:
            files_info = metadata["files"]
            chunks_info = metadata["chunks"]
        
        active_count = sum(1 for s in chunk_servers.values() if s["status"] == "active")
        total_count = len(chunk_servers)
        fault_tolerance = (active_count / total_count * 100) if total_count > 0 else 0
        
        response = {
            "servers": servers_status,
            "files": files_info,
            "chunks": chunks_info,
            "fault_tolerance": round(fault_tolerance, 2),
            "timestamp": datetime.now().isoformat()
        }
        
        self._set_headers()
        self.wfile.write(json.dumps(response).encode())
    
    def _handle_heartbeat(self, data):
        """Handle heartbeat from chunk server"""
        server_id = data.get("server_id")
        host = data.get("host", "unknown")
        port = data.get("port", 0)
        
        if server_id:
            register_chunk_server(server_id, host, port)
            self._set_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode())
        else:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Missing server_id"}).encode())
    
    def _handle_login(self, data):
        """Authenticate user and create session"""
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            self._set_headers(400)
            self.wfile.write(json.dumps({"success": False, "error": "Missing credentials"}).encode())
            return
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if username in users and users[username]["password"] == password_hash:
            token = create_session(username, users[username]["role"])
            
            self._set_headers()
            self.wfile.write(json.dumps({
                "success": True,
                "role": users[username]["role"],
                "username": username,
                "token": token
            }).encode())
        else:
            self._set_headers(401)
            self.wfile.write(json.dumps({"success": False, "error": "Invalid credentials"}).encode())
    
    def _handle_logout(self, data):
        """Logout user and invalidate session"""
        token = data.get("token")
        
        if token:
            with session_lock:
                if token in sessions:
                    del sessions[token]
                    save_sessions()
        
        self._set_headers()
        self.wfile.write(json.dumps({"success": True}).encode())
    
    def _handle_signup(self, data):
        """Public signup - creates basic user account"""
        username = data.get("username")
        password = data.get("password")
        
        if not username or not password:
            self._set_headers(400)
            self.wfile.write(json.dumps({"success": False, "error": "Missing credentials"}).encode())
            return
        
        if username in users:
            self._set_headers(400)
            self.wfile.write(json.dumps({"success": False, "error": "Username already exists"}).encode())
            return
        
        # Create new user with default role
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        users[username] = {
            "password": password_hash,
            "role": "user",
            "created_by": "self",
            "created_at": datetime.now().isoformat()
        }
        save_users()
        
        self._set_headers()
        self.wfile.write(json.dumps({"success": True, "message": "Account created successfully"}).encode())
    
    def _handle_get_users(self):
        """Get all users (admin only)"""
        user_list = [{
            "username": username,
            "role": info["role"],
            "created_by": info.get("created_by", "unknown")
        } for username, info in users.items()]
        
        self._set_headers()
        self.wfile.write(json.dumps({"users": user_list}).encode())
    
    def _handle_create_user(self, data):
        """Create new user (admin/manager only)"""
        username = data.get("username")
        password = data.get("password")
        role = data.get("role", "user")
        created_by = data.get("created_by", "admin")
        
        if username in users:
            self._set_headers(400)
            self.wfile.write(json.dumps({"success": False, "error": "User exists"}).encode())
            return
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        users[username] = {
            "password": password_hash,
            "role": role,
            "created_by": created_by,
            "created_at": datetime.now().isoformat()
        }
        save_users()
        
        self._set_headers()
        self.wfile.write(json.dumps({"success": True}).encode())
    
    def _handle_promote_user(self, data):
        """Promote user to manager"""
        username = data.get("username")
        
        if username not in users:
            self._set_headers(404)
            self.wfile.write(json.dumps({"success": False, "error": "User not found"}).encode())
            return
        
        users[username]["role"] = "manager"
        save_users()
        
        self._set_headers()
        self.wfile.write(json.dumps({"success": True}).encode())
    
    def _handle_allocate_chunks(self, data):
        """Allocate chunks for a file upload"""
        filename = data.get("filename")
        filesize = data.get("filesize", 0)
        
        num_chunks = (filesize + CHUNK_SIZE - 1) // CHUNK_SIZE
        
        with heartbeat_lock:
            active_servers = [sid for sid, info in chunk_servers.items() 
                            if info["status"] == "active"]
        
        if not active_servers:
            self._set_headers(503)
            self.wfile.write(json.dumps({"error": "No active servers"}).encode())
            return
        
        allocations = []
        for i in range(num_chunks):
            chunk_id = f"{filename}_chunk_{i}"
            servers = [active_servers[j % len(active_servers)] 
                      for j in range(i, i + min(REPLICATION_FACTOR, len(active_servers)))]
            allocations.append({
                "chunk_id": chunk_id,
                "servers": servers,
                "index": i
            })
        
        self._set_headers()
        self.wfile.write(json.dumps({"allocations": allocations}).encode())
    
    def _handle_register_chunk(self, data):
        """Register completed chunk upload"""
        filename = data.get("filename")
        chunk_id = data.get("chunk_id")
        servers = data.get("servers", [])
        
        with metadata_lock:
            if filename not in metadata["files"]:
                metadata["files"][filename] = {
                    "chunks": [],
                    "upload_time": datetime.now().isoformat()
                }
            
            metadata["files"][filename]["chunks"].append(chunk_id)
            metadata["chunks"][chunk_id] = {
                "servers": servers,
                "filename": filename
            }
            save_metadata()
        
        self._set_headers()
        self.wfile.write(json.dumps({"success": True}).encode())
    
    def _handle_simulate_failure(self, data):
        """Simulate server failure"""
        server_id = data.get("server_id")
        
        if server_id not in chunk_servers:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Server not found"}).encode())
            return
        
        with heartbeat_lock:
            chunk_servers[server_id]["status"] = "failed"
            chunk_servers[server_id]["last_heartbeat"] = 0
        
        threading.Thread(target=re_replicate_chunks, args=(server_id,), daemon=True).start()
        
        self._set_headers()
        self.wfile.write(json.dumps({"success": True}).encode())
    
    def _handle_logs(self):
        """Return system logs"""
        logs = []
        
        with heartbeat_lock:
            for sid, info in chunk_servers.items():
                logs.append({
                    "timestamp": datetime.fromtimestamp(info["last_heartbeat"]).isoformat(),
                    "server": sid,
                    "event": f"Status: {info['status']}"
                })
        
        self._set_headers()
        self.wfile.write(json.dumps({"logs": logs[-50:]}).encode())
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass

def main():
    load_data()
    
    # Start heartbeat monitor
    threading.Thread(target=check_heartbeats, daemon=True).start()
    
    # Start HTTP server
    server = HTTPServer(('0.0.0.0', 8000), MasterHandler)
    print("[MASTER] Master Node started on port 8000")
    server.serve_forever()

if __name__ == "__main__":
    main()