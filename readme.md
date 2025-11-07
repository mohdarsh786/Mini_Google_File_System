# Mini Google File System (GFS) Simulation

A complete distributed file system simulation inspired by Google File System, featuring fault tolerance, automatic replication, and a comprehensive web-based management dashboard.

## 🎯 Features

- **Distributed Storage**: File chunks distributed across multiple servers
- **Fault Tolerance**: Automatic failure detection and re-replication
- **Heartbeat Monitoring**: Real-time server health tracking
- **Role-Based Access Control**: Admin, Manager, and User roles with different permissions
- **Web Dashboard**: Interactive UI for system management and monitoring
- **Containerized Architecture**: Full Docker deployment with docker-compose

## 🏗️ Architecture

### Components

1. **Master Node** (Port 8000)
   - Manages metadata and chunk assignments
   - Tracks heartbeats from chunk servers
   - Detects failures and triggers re-replication
   - Provides REST API for dashboard and clients

2. **Chunk Servers** (3 instances: Ports 9001-9003)
   - Store file chunks
   - Send periodic heartbeats to Master
   - Handle upload/download requests

3. **Client Service** (Port 8001)
   - Processes file uploads from web UI
   - Splits files into chunks
   - Distributes chunks to assigned servers

4. **Web Interface** (Port 8080)
   - Single-page application
   - Role-based dashboards
   - Real-time system monitoring

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Modern web browser (Chrome, Firefox, Safari, Edge)

## 🚀 Quick Start

### 1. Project Setup

Create the following directory structure:

```
project-root/
├── backend/
│   ├── master_node.py
│   ├── chunk_server.py
│   └── client_script.py
├── web/
│   ├── index.html
│   ├── styles.css
│   └── script.js
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### 2. Build and Start

```bash
# Build and start all containers
docker-compose up -d --build

# Verify all containers are running
docker-compose ps
```

Expected output:
```
NAME            STATUS          PORTS
gfs_master      Up (healthy)    0.0.0.0:8000->8000/tcp
gfs_chunk_1     Up              
gfs_chunk_2     Up              
gfs_chunk_3     Up              
gfs_client      Up              0.0.0.0:8001->8001/tcp
gfs_web         Up              0.0.0.0:8080->80/tcp
```

### 3. Access the Dashboard

Open your browser and navigate to:
```
http://localhost:8080
```

## 👥 User Roles & Credentials

### Default Accounts

| Username  | Password    | Role    | Capabilities |
|-----------|-------------|---------|--------------|
| admin     | admin123    | Admin   | Full system access, user management, fault simulation |
| manager1  | manager123  | Manager | Monitor system, manage files, simulate faults |
| user1     | user123     | User    | Upload files, view personal files, monitor system |

## 📊 Dashboard Features

### Admin Dashboard
- **System Status**: Real-time server health and fault tolerance metrics
- **User Management**: Create users, promote to Manager role
- **Chunk Servers**: Monitor all servers, simulate failures
- **File Distribution**: View all uploaded files and chunk locations
- **Fault Simulation**: Test system resilience by simulating server failures

### Manager Dashboard
- **System Overview**: Monitor active servers and fault tolerance
- **Server Management**: View server status, simulate failures
- **File Transfers**: Track all file uploads and distributions

### User Dashboard
- **File Upload**: Upload files with automatic chunking and distribution
- **Upload Progress**: Real-time visual feedback on upload status
- **System Health**: View server status and fault tolerance
- **My Files**: View personal uploaded files and chunk distribution

## 🔧 Usage Guide

### Uploading a File

1. Login as `user1` (password: `user123`)
2. Navigate to "Upload File" section
3. Enter a filename (e.g., `document.txt`)
4. Enter or paste content
5. Click "Upload File"
6. Watch real-time progress as chunks are distributed

### Simulating Server Failure

1. Login as `admin` or `manager1`
2. Navigate to "Chunk Servers" section
3. Click "Simulate Failure" on any active server
4. Observe automatic re-replication of chunks
5. System automatically redistributes affected chunks to healthy servers

### Creating New Users

1. Login as `admin`
2. Click "+ Add User" button
3. Enter username, password, and select role
4. New user can immediately login with created credentials

## 🔍 Monitoring & Logs

### View Container Logs

```bash
# All services
docker-compose logs -f

# Master node only
docker-compose logs -f master

# Specific chunk server
docker-compose logs -f chunk_server_1

# Client service
docker-compose logs -f client
```

### Check System Status

```bash
# Via API
curl http://localhost:8000/status | python3 -m json.tool

# Container health
docker-compose ps
```

## 🛠️ Advanced Configuration

### Adjust Heartbeat Timeout

Edit `backend/master_node.py`:
```python
HEARTBEAT_TIMEOUT = 15  # seconds (default)
```

### Change Replication Factor

Edit `backend/master_node.py`:
```python
REPLICATION_FACTOR = 2  # default: 2 replicas per chunk
```

### Modify Chunk Size

Edit both `backend/master_node.py` and `backend/client_script.py`:
```python
CHUNK_SIZE = 1024 * 1024  # 1MB (default)
```

## 🐛 Troubleshooting

### Containers Not Starting

```bash
# Check logs
docker-compose logs

# Rebuild from scratch
docker-compose down -v
docker-compose up -d --build
```

### Cannot Access Dashboard

1. Verify web container is running: `docker-compose ps web`
2. Check port isn't in use: `lsof -i :8080` (Mac/Linux)
3. Try accessing: `http://127.0.0.1:8080`

### Upload Failures

1. Ensure all chunk servers are active (check dashboard)
2. Verify client container is running: `docker-compose ps client`
3. Check client logs: `docker-compose logs client`

### Server Not Responding to Heartbeats

```bash
# Restart specific chunk server
docker-compose restart chunk_server_1

# Check network connectivity
docker-compose exec master ping chunk_server_1
```

## 📈 System Behavior

### Fault Detection
- Chunk servers send heartbeats every 5 seconds
- Master marks server as failed after 15 seconds of no heartbeat
- Automatic re-replication begins immediately

### Re-Replication
- Chunks from failed server are identified
- New server assignments calculated using hash distribution
- Chunks re-replicated to maintain replication factor
- Metadata updated atomically

### File Upload Flow
1. Client requests chunk allocation from Master
2. Master assigns chunks to available servers
3. Client uploads chunks to assigned servers (parallel)
4. Client registers completed chunks with Master
5. Master updates metadata persistently

## 🔒 Security Notes

This is a simulation for educational purposes. For production use:
- Implement proper authentication (JWT, OAuth)
- Use HTTPS for all communications
- Add input validation and sanitization
- Implement rate limiting
- Add encryption for data at rest and in transit

## 🛑 Stopping the System

```bash
# Stop all containers (preserves data)
docker-compose stop

# Stop and remove containers (preserves volumes)
docker-compose down

# Complete cleanup (removes all data)
docker-compose down -v
```

## 📚 Technical Details

### Network Architecture
- User-defined bridge network: `gfs_network`
- Container-to-container communication via service names
- External access via published ports

### Data Persistence
- Master metadata: `/data/master/chunks.json`
- User database: `/data/master/users.json`
- Chunk storage: `/data/chunks/<chunk_id>` per server
- Docker volumes ensure data persistence across restarts

### API Endpoints

**Master Node (Port 8000)**
- `GET /status` - System status and metrics
- `POST /heartbeat` - Chunk server heartbeat
- `POST /login` - User authentication
- `GET /users` - List all users
- `POST /create_user` - Create new user
- `POST /promote_user` - Promote user to manager
- `POST /allocate_chunks` - Request chunk allocation
- `POST /register_chunk` - Register uploaded chunk
- `POST /simulate_failure` - Simulate server failure

**Client Service (Port 8001)**
- `POST /upload` - Upload file for distribution

## 🎓 Learning Objectives

This simulation demonstrates:
- Distributed system architecture
- Fault tolerance and recovery
- Metadata management
- Heartbeat-based health monitoring
- Chunk-based storage
- RESTful API design
- Container orchestration
- Role-based access control

## 📝 License

This is an educational project. Feel free to use and modify for learning purposes.

## 🤝 Contributing

This is a simulation project for educational purposes. Suggestions and improvements are welcome!

## 📧 Support

For issues or questions, check the troubleshooting section or review container logs for detailed error information.