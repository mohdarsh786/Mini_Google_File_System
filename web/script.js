// Configuration
const MASTER_URL = 'http://localhost:8000';
const CLIENT_URL = 'http://localhost:8001';
const REFRESH_INTERVAL = 3000; // 3 seconds

// Global state
let currentUser = null;
let currentRole = null;
let refreshTimer = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
});

function initializeApp() {
    // Check if user is already logged in
    const savedUser = localStorage.getItem('gfs_user');
    const savedRole = localStorage.getItem('gfs_role');
    
    if (savedUser && savedRole) {
        currentUser = savedUser;
        currentRole = savedRole;
        showDashboard();
    } else {
        showLogin();
    }
    
    // Setup event listeners
    setupEventListeners();
}

function setupEventListeners() {
    // Login form
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    
    // Logout button
    document.getElementById('logoutBtn').addEventListener('click', handleLogout);
    
    // User management
    const addUserBtn = document.getElementById('addUserBtn');
    if (addUserBtn) {
        addUserBtn.addEventListener('click', () => showModal('addUserModal'));
    }
    
    const cancelBtn = document.getElementById('cancelAddUser');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => hideModal('addUserModal'));
    }
    
    document.getElementById('addUserForm').addEventListener('submit', handleAddUser);
    
    // File upload
    const uploadBtn = document.getElementById('uploadBtn');
    if (uploadBtn) {
        uploadBtn.addEventListener('click', handleFileUpload);
    }
    
    // Modal close
    document.querySelectorAll('.close').forEach(el => {
        el.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) hideModal(modal.id);
        });
    });
}

// Authentication
async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorEl = document.getElementById('loginError');
    
    try {
        const response = await fetch(`${MASTER_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser = username;
            currentRole = data.role;
            
            localStorage.setItem('gfs_user', username);
            localStorage.setItem('gfs_role', data.role);
            
            showDashboard();
        } else {
            errorEl.textContent = data.error || 'Login failed';
        }
    } catch (error) {
        errorEl.textContent = 'Connection error. Please ensure the system is running.';
        console.error('Login error:', error);
    }
}

function handleLogout() {
    currentUser = null;
    currentRole = null;
    localStorage.removeItem('gfs_user');
    localStorage.removeItem('gfs_role');
    
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }
    
    showLogin();
}

// Screen management
function showLogin() {
    document.getElementById('loginScreen').classList.add('active');
    document.getElementById('dashboardScreen').classList.remove('active');
    document.getElementById('loginForm').reset();
    document.getElementById('loginError').textContent = '';
}

function showDashboard() {
    document.getElementById('loginScreen').classList.remove('active');
    document.getElementById('dashboardScreen').classList.add('active');
    
    document.getElementById('userName').textContent = currentUser;
    document.getElementById('userRole').textContent = currentRole;
    
    // Show appropriate dashboard
    document.querySelectorAll('.dashboard-content').forEach(el => {
        el.classList.remove('active');
    });
    
    if (currentRole === 'admin') {
        document.getElementById('adminDashboard').classList.add('active');
        loadAdminDashboard();
    } else if (currentRole === 'manager') {
        document.getElementById('managerDashboard').classList.add('active');
        loadManagerDashboard();
    } else {
        document.getElementById('userDashboard').classList.add('active');
        loadUserDashboard();
    }
    
    // Start auto-refresh
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(refreshDashboard, REFRESH_INTERVAL);
}

function refreshDashboard() {
    if (currentRole === 'admin') {
        loadAdminDashboard();
    } else if (currentRole === 'manager') {
        loadManagerDashboard();
    } else {
        loadUserDashboard();
    }
}

// Admin Dashboard
async function loadAdminDashboard() {
    try {
        const [status, users] = await Promise.all([
            fetch(`${MASTER_URL}/status`).then(r => r.json()),
            fetch(`${MASTER_URL}/users`).then(r => r.json())
        ]);
        
        updateAdminStats(status);
        updateServersList(status.servers, 'serversList', true);
        updateUsersList(users.users);
        updateFilesList(status.files, 'filesList');
    } catch (error) {
        console.error('Error loading admin dashboard:', error);
    }
}

function updateAdminStats(status) {
    const activeCount = Object.values(status.servers).filter(s => s.status === 'active').length;
    const fileCount = Object.keys(status.files).length;
    
    document.getElementById('activeServers').textContent = `${activeCount}/${Object.keys(status.servers).length}`;
    document.getElementById('totalFiles').textContent = fileCount;
    document.getElementById('faultTolerance').textContent = `${status.fault_tolerance}%`;
    document.getElementById('totalUsers').textContent = document.querySelectorAll('.user-row').length - 1;
}

function updateUsersList(users) {
    const container = document.getElementById('usersTable');
    
    let html = `
        <div class="user-row">
            <div>Username</div>
            <div>Role</div>
            <div>Created By</div>
            <div>Actions</div>
        </div>
    `;
    
    users.forEach(user => {
        html += `
            <div class="user-row">
                <div>${user.username}</div>
                <div>${user.role}</div>
                <div>${user.created_by}</div>
                <div>
                    ${user.role === 'user' ? `<button class="btn-primary" onclick="promoteUser('${user.username}')">Promote to Manager</button>` : '-'}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function promoteUser(username) {
    try {
        const response = await fetch(`${MASTER_URL}/promote_user`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username })
        });
        
        const data = await response.json();
        if (data.success) {
            alert(`User ${username} promoted to Manager`);
            loadAdminDashboard();
        } else {
            alert('Failed to promote user');
        }
    } catch (error) {
        console.error('Error promoting user:', error);
        alert('Error promoting user');
    }
}

// Manager Dashboard
async function loadManagerDashboard() {
    try {
        const status = await fetch(`${MASTER_URL}/status`).then(r => r.json());
        
        updateManagerStats(status);
        updateServersList(status.servers, 'managerServersList', true);
        updateFilesList(status.files, 'managerFilesList');
    } catch (error) {
        console.error('Error loading manager dashboard:', error);
    }
}

function updateManagerStats(status) {
    const activeCount = Object.values(status.servers).filter(s => s.status === 'active').length;
    const fileCount = Object.keys(status.files).length;
    
    document.getElementById('managerActiveServers').textContent = `${activeCount}/${Object.keys(status.servers).length}`;
    document.getElementById('managerTotalFiles').textContent = fileCount;
    document.getElementById('managerFaultTolerance').textContent = `${status.fault_tolerance}%`;
}

// User Dashboard
async function loadUserDashboard() {
    try {
        const status = await fetch(`${MASTER_URL}/status`).then(r => r.json());
        
        updateUserStats(status);
        updateServersList(status.servers, 'userServersList', false);
        updateFilesList(status.files, 'userFilesList');
    } catch (error) {
        console.error('Error loading user dashboard:', error);
    }
}

function updateUserStats(status) {
    const activeCount = Object.values(status.servers).filter(s => s.status === 'active').length;
    const fileCount = Object.keys(status.files).length;
    
    document.getElementById('userActiveServers').textContent = `${activeCount}/${Object.keys(status.servers).length}`;
    document.getElementById('userTotalFiles').textContent = fileCount;
    document.getElementById('userFaultTolerance').textContent = `${status.fault_tolerance}%`;
}

// Servers List
function updateServersList(servers, containerId, showActions) {
    const container = document.getElementById(containerId);
    
    if (!servers || Object.keys(servers).length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No servers available</p></div>';
        return;
    }
    
    let html = '';
    
    Object.entries(servers).forEach(([id, info]) => {
        const statusClass = info.status === 'active' ? 'active' : 'failed';
        const lastHeartbeat = new Date(info.last_heartbeat * 1000).toLocaleTimeString();
        
        html += `
            <div class="server-card ${statusClass}">
                <div class="server-header">
                    <div class="server-name">${id}</div>
                    <div class="server-status ${statusClass}">${info.status}</div>
                </div>
                <div class="server-info">Host: ${info.host}:${info.port}</div>
                <div class="server-info">Last Heartbeat: ${lastHeartbeat}</div>
                ${showActions && (currentRole === 'admin' || currentRole === 'manager') ? `
                    <div class="server-actions">
                        <button class="btn-danger" onclick="simulateFailure('${id}')" ${info.status === 'failed' ? 'disabled' : ''}>
                            Simulate Failure
                        </button>
                    </div>
                ` : ''}
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function simulateFailure(serverId) {
    if (!confirm(`Are you sure you want to simulate failure of ${serverId}?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${MASTER_URL}/simulate_failure`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ server_id: serverId })
        });
        
        const data = await response.json();
        if (data.success) {
            alert(`Server ${serverId} marked as failed. Re-replication in progress...`);
            refreshDashboard();
        } else {
            alert('Failed to simulate failure');
        }
    } catch (error) {
        console.error('Error simulating failure:', error);
        alert('Error simulating failure');
    }
}

// Files List
function updateFilesList(files, containerId) {
    const container = document.getElementById(containerId);
    
    if (!files || Object.keys(files).length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No files uploaded yet</p></div>';
        return;
    }
    
    let html = '';
    
    Object.entries(files).forEach(([filename, info]) => {
        html += `
            <div class="file-card">
                <div class="file-name">📄 ${filename}</div>
                <div>Uploaded: ${new Date(info.upload_time).toLocaleString()}</div>
                <div>Chunks: ${info.chunks.length}</div>
                <div class="file-chunks">
                    ${info.chunks.map(chunk => `<span class="chunk-badge">${chunk}</span>`).join('')}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// File Upload
async function handleFileUpload() {
    const filename = document.getElementById('fileName').value.trim();
    const content = document.getElementById('fileContent').value;
    
    if (!filename) {
        alert('Please enter a filename');
        return;
    }
    
    if (!content) {
        alert('Please enter file content');
        return;
    }
    
    const progressContainer = document.getElementById('uploadProgress');
    progressContainer.innerHTML = '<div class="progress-item loading"><div class="progress-label">Uploading...</div></div>';
    
    try {
        const response = await fetch(`${CLIENT_URL}/upload`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename, content })
        });
        
        const data = await response.json();
        
        if (data.success) {
            progressContainer.innerHTML = `
                <div class="progress-item">
                    <div class="progress-label">✓ Upload successful: ${data.filename} (${data.size} bytes)</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: 100%"></div>
                    </div>
                </div>
            `;
            
            document.getElementById('fileName').value = '';
            document.getElementById('fileContent').value = '';
            
            setTimeout(() => {
                loadUserDashboard();
            }, 2000);
        } else {
            progressContainer.innerHTML = '<div class="progress-item"><div class="progress-label">❌ Upload failed</div></div>';
        }
    } catch (error) {
        console.error('Upload error:', error);
        progressContainer.innerHTML = '<div class="progress-item"><div class="progress-label">❌ Connection error. Please ensure the client service is running.</div></div>';
    }
}

// User Management
async function handleAddUser(e) {
    e.preventDefault();
    
    const username = document.getElementById('newUsername').value;
    const password = document.getElementById('newPassword').value;
    const role = document.getElementById('newUserRole').value;
    
    try {
        const response = await fetch(`${MASTER_URL}/create_user`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username,
                password,
                role,
                created_by: currentUser
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`User ${username} created successfully`);
            hideModal('addUserModal');
            document.getElementById('addUserForm').reset();
            loadAdminDashboard();
        } else {
            alert(data.error || 'Failed to create user');
        }
    } catch (error) {
        console.error('Error creating user:', error);
        alert('Error creating user');
    }
}

// Modal functions
function showModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function hideModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Make functions global for onclick handlers
window.promoteUser = promoteUser;
window.simulateFailure = simulateFailure;