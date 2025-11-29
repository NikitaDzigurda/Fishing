/**
 * dashboard-logic.js
 * Updated with API integration for Search and Profile.
 */

// --- HELPERS ---

// Get cookie utility
const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
};

// Generic API Client with Auth
const apiCall = async (endpoint, options = {}) => {
    const token = getCookie('access_token');
    
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...options.headers
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            // Token expired or invalid
            window.location.href = 'login.html';
            return null;
        }

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'API Request Failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        alert(error.message);
        return null;
    }
};

// --- MOCK DATA GENERATORS (Kept for Charts/Feed/Admin only) ---

const getMockChartData = () => {
    return Array.from({ length: 12 }, () => Math.floor(Math.random() * 80) + 20);
};

const getMockFeed = () => {
    return [
        {
            id: 1,
            title: "Project: CHRONOS",
            author: "Dr. E. Brown",
            desc: "Looking for a specialist in high-energy plasma physics to stabilize the flux capacitor prototype.",
            tags: ["Physics", "Energy", "Hard Science"],
            req: "PhD in Physics or equivalent experience."
        },
        {
            id: 2,
            title: "Neural Link Interface",
            author: "CyberDyne Systems",
            desc: "Need a backend developer to optimize data throughput from BCI (Brain-Computer Interface) devices.",
            tags: ["Backend", "Neuroscience", "Python"],
            req: "Experience with real-time data processing."
        }
    ];
};

// --- STATE MANAGEMENT ---

let currentUserRole = 'guest'; // Defaults to guest until API confirms
let currentTab = 'home';

// --- CORE RENDER FUNCTIONS ---

// NEW: Async initialization that checks the API
async function initDashboardUI() {
    const nameEl = document.getElementById('user-name');
    const roleEl = document.getElementById('user-role');
    const container = document.getElementById('main-content');

    // 1. Visual Loading State in Sidebar
    if (nameEl) nameEl.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i>';
    
    try {
        // 2. Call API: GET /api/v1/auth/me
        // Note: apiCall automatically redirects to login.html if it gets a 401
        const userData = await apiCall('/auth/me');

        if (!userData) return; // Stop if redirecting or error

        // 3. Determine Role
        // API returns: { id: 1, email: "...", role: "admin" | "observer", is_active: true }
        if (userData.role === 'admin') {
            currentUserRole = 'admin';
        } else {
            // Treat 'observer' or any future roles as standard 'user' for now
            currentUserRole = 'user';
        }

        // 4. Update Sidebar Info
        if (nameEl) nameEl.innerText = userData.email;
        if (roleEl) {
            roleEl.innerText = userData.role.toUpperCase();
            
            // Color coding for role
            roleEl.className = 'text-xs truncate font-bold ' + 
                (userData.role === 'admin' ? 'text-red-400' : 'text-cyan-400');
        }

        // 5. Store user ID/Email for other functions (like profile view)
        localStorage.setItem('userId', userData.id);
        localStorage.setItem('username', userData.email);

        // 6. Render Dashboard
        renderNavigation();
        navigateTo('home');

    } catch (error) {
        console.error("Initialization Failed:", error);
        // Fallback to login if something critical fails
        window.location.href = 'login.html';
    }
}

function renderNavigation() {
    const nav = document.getElementById('main-nav');
    nav.innerHTML = '';

    const createBtn = (id, icon, text, onClick) => {
        const btn = document.createElement('button');
        btn.className = `nav-btn ${currentTab === id ? 'active' : ''}`;
        btn.dataset.id = id;
        btn.innerHTML = `<i class="fa-solid ${icon}"></i> ${text}`;
        btn.onclick = () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            onClick();
        };
        nav.appendChild(btn);
    };

    // --- DYNAMIC NAVIGATION BASED ON API ROLE ---
    
    if (currentUserRole === 'admin') {
        // ADMIN DASHBOARD
        createBtn('home', 'fa-chart-line', 'ANALYTICS', () => navigateTo('home'));
        createBtn('upload', 'fa-file-csv', 'UPLOAD CSV', () => navigateTo('upload'));
        createBtn('search', 'fa-magnifying-glass', 'USER BASE', () => navigateTo('search'));
    } 
    else {
        // OBSERVER / USER DASHBOARD
        createBtn('home', 'fa-list-check', 'REQUESTS FEED', () => navigateTo('home'));
        createBtn('search', 'fa-users', 'FIND SCIENTISTS', () => navigateTo('search'));
        createBtn('profile', 'fa-id-card', 'MY PROFILE', () => navigateTo('profile'));
        
        // Example: Only show "New Request" if they have a specific permission (optional)
        // createBtn('create', 'fa-plus', 'NEW REQUEST', () => navigateTo('create'));
    }
}

function navigateTo(tab) {
    currentTab = tab;
    const container = document.getElementById('main-content');
    container.innerHTML = ''; 
    container.style.opacity = 0;

    setTimeout(() => {
        switch (tab) {
            case 'home':
                // Logic switches based on the role determined in initDashboardUI
                if (currentUserRole === 'admin') {
                    renderAdminDashboard(container);
                } else {
                    renderFeed(container);
                }
                break;
            case 'upload':
                renderUpload(container);
                break;
            case 'search':
                renderUserSearch(container);
                break;
            case 'create':
                renderCreateRequest(container);
                break;
            case 'profile':
                // Loads the profile of the currently logged in user
                loadOwnProfile(container);
                break;
        }
        container.style.transition = 'opacity 0.3s';
        container.style.opacity = 1;
    }, 100);
}
// --- TAB CONTENT RENDERERS ---

// 1. ADMIN DASHBOARD (Mocked)
function renderAdminDashboard(container) {
    const data = getMockChartData();
    container.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fade-in">
            <div class="tech-card p-6 rounded-xl">
                <h3 class="text-xl text-cyan-400 mb-4"><i class="fa-solid fa-signal mr-2"></i> SYSTEM ACTIVITY</h3>
                <div class="chart-container">
                    ${data.map(h => `<div class="chart-bar" style="height: ${h}%"></div>`).join('')}
                </div>
            </div>
             <div class="tech-card p-6 rounded-xl flex flex-col justify-center text-center">
                <h3 class="text-xl text-cyan-400 mb-4">ACTIVE NODES</h3>
                <div class="text-4xl font-bold text-white">1,024</div>
            </div>
        </div>
    `;
}

// 2. CSV UPLOAD (Mocked)
function renderUpload(container) {
    container.innerHTML = `
        <div class="tech-card max-w-2xl mx-auto p-10 rounded-xl text-center">
            <h2 class="text-3xl font-bold mb-6">UPLOAD USER DATABASE</h2>
            <div class="border-2 border-dashed border-slate-600 hover:border-cyan-400 rounded-xl p-10 transition-colors cursor-pointer bg-slate-900/50">
                <i class="fa-solid fa-cloud-arrow-up text-6xl text-slate-500 mb-4"></i>
                <p>Drag & Drop CSV file here</p>
                <input type="file" class="hidden">
            </div>
        </div>
    `;
}

// 3. USER SEARCH (REAL API)
function renderUserSearch(container) {
    // Basic Layout
    container.innerHTML = `
        <div class="mb-6 flex gap-4">
            <input type="text" id="search-input" placeholder="Search by name, university or skills..." 
                class="w-full bg-slate-900/80 border border-slate-700 rounded-lg p-4 text-white focus:border-cyan-400 outline-none">
            <button id="search-btn" class="bg-cyan-900/50 border border-cyan-500/50 text-cyan-400 px-6 rounded-lg hover:bg-cyan-900 transition-all">
                <i class="fa-solid fa-filter"></i>
            </button>
        </div>
        <div id="search-results-grid" class="user-card-grid">
            <div class="col-span-full text-center text-slate-500 py-10">
                <i class="fa-solid fa-magnifying-glass text-4xl mb-3"></i>
                <p>Enter a query to find scientists in the database.</p>
            </div>
        </div>
    `;

    const input = document.getElementById('search-input');
    const btn = document.getElementById('search-btn');

    const doSearch = () => {
        const query = input.value.trim();
        if (query.length > 0) {
            handleUserSearch(query);
        }
    };

    // Events
    btn.onclick = doSearch;
    input.addEventListener('keyup', (e) => {
        if (e.key === 'Enter') doSearch();
    });
}

// Helper to execute search
async function handleUserSearch(query) {
    const grid = document.getElementById('search-results-grid');
    grid.innerHTML = '<div class="col-span-full text-center"><i class="fa-solid fa-circle-notch fa-spin text-cyan-400 text-2xl"></i></div>';

    // API Call: /api/v1/profile/search?q=...
    const data = await apiCall(`/profile/search?q=${encodeURIComponent(query)}&limit=12`);

    if (!data || data.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full text-center text-slate-500 py-10">
                <p>No profiles found matching "${query}".</p>
            </div>`;
        return;
    }

    // Render Cards
    grid.innerHTML = data.map(profile => {
        const fullName = `${profile.first_name || 'Unknown'} ${profile.last_name || ''}`.trim();
        const role = profile.major || 'Researcher';
        const uni = profile.university || 'No University';
        const bio = profile.bio || 'No bio available.';
        const avatarColor = `hsl(${(profile.id * 137) % 360}, 70%, 60%)`; // Deterministic color based on ID

        return `
            <div class="info-card p-4 rounded-xl flex flex-col gap-4 relative overflow-hidden group">
                <div class="absolute top-0 left-0 w-1 h-full bg-cyan-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 rounded-full flex items-center justify-center text-slate-900 font-bold text-xl" style="background-color: ${avatarColor}">
                        ${fullName.charAt(0)}
                    </div>
                    <div>
                        <h4 class="font-bold text-lg leading-tight">${fullName}</h4>
                        <p class="text-xs text-cyan-400 uppercase tracking-widest truncate w-40">${role}</p>
                    </div>
                </div>
                <div class="text-sm text-slate-400 h-10 overflow-hidden text-ellipsis line-clamp-2">
                    ${bio}
                </div>
                <div class="text-xs text-slate-500 flex items-center gap-2">
                        <i class="fa-solid fa-graduation-cap"></i> <span class="truncate w-48">${uni}</span>
                </div>
                <button onclick="viewUser(${profile.user_id})" class="mt-auto w-full py-2 border border-slate-600 rounded hover:bg-cyan-500/10 hover:border-cyan-400 text-sm transition-all">
                    VIEW PROFILE
                </button>
            </div>
        `;
    }).join('');
}

// 4. FEED (Mocked)
function renderFeed(container) {
    const feed = getMockFeed();
    container.innerHTML = `
        <h2 class="text-2xl orbitron-font mb-6 text-left border-b border-slate-800 pb-2">
            <i class="fa-solid fa-satellite-dish text-cyan-400 mr-2"></i> CURRENT RESEARCH REQUESTS
        </h2>
        <div class="flex flex-col gap-4">
            ${feed.map(item => `
                <div class="tech-card p-6 rounded-xl flex flex-col md:flex-row gap-6 items-start md:items-center hover:bg-slate-900/80 transition-colors">
                    <div class="flex-grow">
                        <h3 class="text-xl font-bold text-white mb-1">${item.title}</h3>
                        <p class="text-slate-300 text-sm mb-3">${item.desc}</p>
                        <div class="flex gap-2 flex-wrap">
                            ${item.tags.map(t => `<span class="tag">${t}</span>`).join('')}
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

// 5. PROFILE (REAL API)

// A. View MY Profile
async function loadOwnProfile(container) {
    container.innerHTML = '<div class="text-center mt-20"><i class="fa-solid fa-circle-notch fa-spin text-4xl text-cyan-400"></i></div>';
    
    // 1. Get User Info
    const userMe = await apiCall('/auth/me'); // Get ID, email
    if (!userMe) return;

    // 2. Get Profile Info
    const profileMe = await apiCall('/profile/me');
    
    // If profile doesn't exist (404/null), we might want to show "Create Profile" form.
    // For now, let's assume it returns empty object or we handle it.
    // Since OpenAPI shows 200 for Get, assume it exists or returns default.
    
    renderProfile(container, profileMe || { user_id: userMe.id }, true);
}

// Expose this function to the global scope so HTML onclick="..." can find it
window.viewUser = async function(id) {
    console.log(`Fetching profile for ID: ${id}`);
    
    const container = document.getElementById('main-content');
    
    // 1. Show Loading State
    container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-64">
            <i class="fa-solid fa-circle-notch fa-spin text-4xl text-cyan-400 mb-4"></i>
            <p class="text-slate-400">Accessing Academic Record...</p>
        </div>
    `;
    
    try {
        // 2. API Call to /api/v1/profile/{id}
        // apiCall automatically prepends /api/v1 and adds Auth headers
        const profile = await apiCall(`/profile/${id}`);

        // 3. Validation
        if (!profile) {
            container.innerHTML = `
                <div class="text-center py-20">
                    <i class="fa-solid fa-user-slash text-4xl text-slate-600 mb-4"></i>
                    <h2 class="text-xl text-slate-400">Profile Not Found</h2>
                    <button onclick="navigateTo('search')" class="mt-4 text-cyan-400 hover:underline">
                        Return to Search
                    </button>
                </div>
            `;
            return;
        }

        // 4. Render the Profile
        // We pass 'false' for isEditable since we are viewing someone else
        renderProfile(container, profile, false);

        // 5. Update UI State (Deselect sidebar buttons to indicate "Detail View")
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    } catch (error) {
        console.error("View User Error:", error);
        container.innerHTML = `<div class="text-red-400 text-center p-10">Error loading profile: ${error.message}</div>`;
    }
};

// C. Render Logic
function renderProfile(container, profile, isEditable) {
    const fullName = `${profile.first_name || ''} ${profile.last_name || ''}`.trim() || 'Anonymous Scientist';
    const uni = profile.university || 'Not specified';
    const major = profile.major || 'General Science';
    const bio = profile.bio || 'No biography provided yet.';
    
    // Metrics (if available in schema)
    const hIndex = profile.h_index || 0;
    const citations = profile.citations_total || 0;

    container.innerHTML = `
        <div class="tech-card max-w-4xl mx-auto p-8 rounded-xl relative animate-fade-in">
            <div class="absolute top-0 right-0 p-4">
               ${isEditable ? '<button onclick="alert(\'Edit Mode Not Implemented in this Demo\')" class="text-slate-500 hover:text-cyan-400"><i class="fa-solid fa-pen-to-square text-xl"></i></button>' : ''}
            </div>
            
            <div class="flex flex-col md:flex-row gap-8 items-center md:items-start border-b border-slate-800 pb-8 mb-8">
                <div class="w-32 h-32 rounded-full bg-slate-800 border-2 border-cyan-400 flex items-center justify-center shadow-[0_0_15px_rgba(34,211,238,0.3)]">
                    <span class="text-4xl font-bold text-cyan-400">${fullName.charAt(0)}</span>
                </div>
                <div class="flex-grow text-center md:text-left">
                    <h2 class="text-3xl font-bold orbitron-font mb-2">${fullName}</h2>
                    <p class="text-cyan-500 tracking-widest uppercase text-sm mb-4">ACADEMIC PROFILE</p>
                    
                    <div class="flex gap-4 justify-center md:justify-start flex-wrap">
                        ${profile.google_scholar_id ? `<span class="tag bg-slate-800 border-slate-600"><i class="fa-brands fa-google"></i> Scholar</span>` : ''}
                        ${profile.orcid ? `<span class="tag bg-slate-800 border-slate-600"><i class="fa-solid fa-id-badge"></i> ORCID</span>` : ''}
                    </div>
                </div>
                 <div class="flex gap-4 text-center">
                    <div class="bg-slate-900 p-3 rounded border border-slate-700 w-24">
                        <div class="text-2xl font-bold text-white">${hIndex}</div>
                        <div class="text-xs text-slate-500">h-index</div>
                    </div>
                    <div class="bg-slate-900 p-3 rounded border border-slate-700 w-24">
                        <div class="text-2xl font-bold text-white">${citations}</div>
                        <div class="text-xs text-slate-500">Citations</div>
                    </div>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                 <div class="space-y-4">
                    <div class="bg-slate-900/50 p-4 rounded border border-slate-700">
                        <div class="text-xs text-slate-500 mb-1">University</div>
                        <div class="font-semibold">${uni}</div>
                    </div>
                    <div class="bg-slate-900/50 p-4 rounded border border-slate-700">
                        <div class="text-xs text-slate-500 mb-1">Major / Field</div>
                        <div class="font-semibold">${major}</div>
                    </div>
                 </div>
                 
                 <div class="bg-slate-900/50 p-4 rounded border border-slate-700 h-full">
                    <div class="text-xs text-slate-500 mb-2">Biography</div>
                    <div class="text-sm text-slate-300 leading-relaxed">${bio}</div>
                </div>
            </div>
            
            ${currentUserRole === 'admin' ? `
            <div class="mt-8 pt-6 border-t border-slate-800 flex justify-end gap-4">
                <button class="text-red-400 border border-red-900/50 px-4 py-2 rounded hover:bg-red-900/20">ADMIN: BAN USER</button>
            </div>
            ` : ''}
        </div>
    `;
}

// 6. CREATE REQUEST (Mocked)
function renderCreateRequest(container) {
    container.innerHTML = `
        <div class="tech-card max-w-2xl mx-auto p-8 rounded-xl">
            <h2 class="text-2xl orbitron-font mb-6 text-center">INITIALIZE TEAM REQUEST</h2>
            <div class="text-center text-slate-500">Feature coming soon...</div>
        </div>
    `;
}