/*
 * dashboard-logic.js — Resolved Version
 */

// --- GLOBAL VARIABLES ---
let currentUserRole = 'guest';
let currentTab = 'home';
let userProfileCache = null; 
let majorTags = []; // Profile tags
let requestRoles = []; // Request creation tags
let isCreatingProfile = false; // Flag: true = POST, false = PATCH
const API_BASE_URL = 'http://localhost:8000/api/v1'; 

// --- MOCK DATA (For Admin/Guest Charts) ---
const getMockChartData = () => {
    return Array.from({ length: 12 }, () => Math.floor(Math.random() * 80) + 20);
};

const getMockFeed = () => {
    return [
        {
            id: 1,
            title: "Project: CHRONOS",
            author: "Dr. E. Brown",
            desc: "Looking for a specialist in high-energy plasma physics.",
            tags: ["Physics", "Energy"],
            req: "PhD in Physics."
        },
        {
            id: 2,
            title: "Neural Link Interface",
            author: "CyberDyne Systems",
            desc: "Need a backend developer to optimize data throughput.",
            tags: ["Backend", "Python"],
            req: "Real-time data processing."
        }
    ];
};

// --- HELPERS ---

const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
};

const apiCall = async (endpoint, options = {}) => {
    const token = getCookie('access_token');
    
    // Default headers
    const headers = {
        'Accept': 'application/json',
        ...options.headers
    };

    // IMPORTANT: Only set JSON content type if body is NOT FormData.
    if (options.body && !(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });

        // Handle 401 Unauthorized
        if (response.status === 401) {
            // For profile checks, don't redirect immediately (let UI handle "Create Profile")
            if (endpoint.includes('/profile/me')) {
                return null;
            }
            window.location.href = 'login.html';
            return null;
        }

        // Handle 404 for profile (Create Mode)
        if (response.status === 404 && endpoint.includes('/profile/me')) {
            return null;
        }

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            
            // Handle Validation Errors (422) nicely
            if (err.detail && Array.isArray(err.detail)) {
                throw new Error(err.detail.map(e => e.msg).join(', '));
            }
            throw new Error(err.detail || 'API request error');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        // Suppress alerts for profile check to avoid annoying popups on login
        if (!endpoint.includes('/profile/me')) {
            // alert(error.message); // Optional: Uncomment to see alerts
        }
        throw error;
    }
};

// --- CORE FUNCTIONS ---

async function initDashboardUI() {
    const nameEl = document.getElementById('user-name');
    const roleEl = document.getElementById('user-role');
    
    // 1. Check LocalStorage for Guest Mode
    const storedType = localStorage.getItem('userType');

    if (storedType === 'guest') {
        currentUserRole = 'guest';
        if (nameEl) nameEl.innerText = 'Guest User';
        if (roleEl) {
            roleEl.innerText = 'GUEST ACCESS';
            roleEl.className = 'text-xs truncate font-bold text-slate-500';
        }
        renderNavigation();
        navigateTo('home');
        return; 
    }

    // 2. Check Token
    if (!getCookie('access_token')) {
        // console.warn("No token found");
        // window.location.href = 'login.html'; // Uncomment for prod
    }

    // Visual Loading State
    if (nameEl) nameEl.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i>';

    try {
        // 3. Call API: GET /api/v1/auth/me (Who am I?)
        const userData = await apiCall('/auth/me');
        if (!userData) return; 

        // Update LocalStorage
        localStorage.setItem('userId', userData.id);
        localStorage.setItem('username', userData.email);

        // Determine Role
        if (userData.role === 'admin') {
            currentUserRole = 'admin';
            updateHeaderUI(userData.email, 'admin');
            renderNavigation();
            navigateTo('home');
        } else {
            currentUserRole = 'user';
            
            // 4. For Users: Check if Profile Exists
            const profile = await apiCall('/profile/me');
            
            if (profile) {
                // Profile exists -> Store it and show Dashboard
                userProfileCache = profile;
                isCreatingProfile = false;
                updateHeaderUI(null, 'user'); // Uses cache
                renderNavigation();
                navigateTo('home');
            } else {
                // Profile missing -> Create Mode
                console.log("Profile missing - Initializing Creation Mode");
                isCreatingProfile = true;
                userProfileCache = null;
                updateHeaderUI(userData.email, 'user');
                
                renderNavigation(true); // Locked navigation
                // Force render edit form in main content
                const container = document.getElementById('main-content');
                if(container) renderProfileEdit(container, {}, true);
            }
        }

    } catch (error) {
        console.error("Initialization Failed:", error);
        if(error.message.includes('401')) {
            window.location.href = 'login.html';
        }
    }
}

function updateHeaderUI(name, type) {
    const nameEl = document.getElementById('user-name');
    const roleEl = document.getElementById('user-role');
    
    // Use cached profile name if available, otherwise email
    let displayName = name;
    if (userProfileCache && userProfileCache.first_name) {
        displayName = `${userProfileCache.first_name} ${userProfileCache.last_name || ''}`.trim();
    }

    if(nameEl) nameEl.innerText = displayName || 'User';
    
    if(roleEl) {
        if (type === 'admin') {
            roleEl.innerText = 'ADMINISTRATOR';
            roleEl.className = 'text-[10px] tracking-widest font-bold uppercase text-red-400';
        } else if (type === 'user') {
            roleEl.innerText = 'SCIENTIST';
            roleEl.className = 'text-[10px] tracking-widest font-bold uppercase text-cyan-400';
        } else {
            roleEl.innerText = 'GUEST';
            roleEl.className = 'text-[10px] tracking-widest font-bold uppercase text-slate-400';
        }
    }
}

function renderNavigation(isLocked = false) {
    const nav = document.getElementById('main-nav');
    if(!nav) return;
    nav.innerHTML = '';

    if (isLocked) {
        nav.innerHTML = `
            <div class="p-4 text-center">
                <i class="fa-solid fa-lock text-slate-600 text-2xl mb-2"></i>
                <p class="text-slate-500 text-xs italic">Please complete your profile to access the system.</p>
            </div>`;
        return;
    }

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

    // --- DYNAMIC NAVIGATION ---
    if (currentUserRole === 'admin') {
        createBtn('home', 'fa-chart-line', 'ANALYTICS', () => navigateTo('home'));
        createBtn('upload', 'fa-file-csv', 'UPLOAD CSV', () => navigateTo('upload'));
        createBtn('search', 'fa-magnifying-glass', 'USER BASE', () => navigateTo('search'));
    } 
    else if (currentUserRole === 'user') {
        createBtn('home', 'fa-list-check', 'FEED', () => navigateTo('home'));
        createBtn('create', 'fa-plus', 'NEW REQUEST', () => navigateTo('create'));
        createBtn('search', 'fa-users', 'SEARCH', () => navigateTo('search'));
        createBtn('profile', 'fa-id-card', 'PROFILE', () => navigateTo('profile'));
    } 
    else {
        // Guest
        createBtn('home', 'fa-eye', 'PUBLIC FEED', () => navigateTo('home'));
        createBtn('search', 'fa-magnifying-glass', 'USER SEARCH', () => navigateTo('search'));
    }
}

function navigateTo(tab) {
    currentTab = tab;
    const container = document.getElementById('main-content');
    if(!container) return;
    
    container.innerHTML = '';
    container.style.opacity = 0;

    // Update buttons state
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const activeBtn = document.querySelector(`.nav-btn[data-id="${tab}"]`);
    if(activeBtn) activeBtn.classList.add('active');

    setTimeout(() => {
        switch (tab) {
            case 'home':
                if (currentUserRole === 'admin') renderAdminDashboard(container);
                else renderFeed(container);
                break;
            case 'upload':
                renderUpload(container);
                break;
            case 'create': 
                renderCreateRequest(container); 
                break;
            case 'search': 
                renderUserSearch(container); 
                break;
            case 'profile': 
                loadOwnProfile(container); 
                break;
        }
        container.style.transition = 'opacity 0.3s';
        container.style.opacity = 1;
    }, 100);
}

// --- ADMIN / UPLOAD CONTENT ---

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

function renderUpload(container) {
    container.innerHTML = `
        <div class="tech-card max-w-2xl mx-auto p-10 rounded-xl text-center animate-fade-in">
            <h2 class="text-3xl font-bold mb-2 text-white">UPLOAD DATABASE</h2>
            <p class="text-slate-400 mb-8">Supported formats: .csv, .xlsx</p>
            
            <!-- Drop Zone -->
            <div id="drop-zone" class="border-2 border-dashed border-slate-600 hover:border-cyan-400 rounded-xl p-10 transition-all cursor-pointer bg-slate-900/50 group relative">
                <input type="file" class="hidden" id="file-input" accept=".csv, .xlsx, .xls">
                <div id="upload-ui-default">
                    <i class="fa-solid fa-cloud-arrow-up text-6xl text-slate-500 group-hover:text-cyan-400 transition-colors mb-4"></i>
                    <p class="text-lg text-slate-300">Drag & Drop file here</p>
                </div>
                <div id="upload-ui-selected" class="hidden">
                    <i class="fa-solid fa-file-csv text-6xl text-cyan-400 mb-4"></i>
                    <p id="file-name" class="text-lg text-white font-bold break-all"></p>
                    <p class="text-sm text-green-400 mt-2"><i class="fa-solid fa-check"></i> Ready to upload</p>
                </div>
                <div id="upload-loading" class="absolute inset-0 bg-slate-900/90 flex flex-col items-center justify-center hidden rounded-xl">
                    <i class="fa-solid fa-circle-notch fa-spin text-4xl text-cyan-400 mb-4"></i>
                    <p class="text-cyan-400 animate-pulse">Processing Data...</p>
                </div>
            </div>

            <div id="status-message" class="mt-4 h-6 text-sm"></div>

            <button id="upload-btn" disabled class="mt-6 bg-slate-700 text-slate-400 cursor-not-allowed px-8 py-3 rounded font-bold transition-all w-full">
                IMPORT DATA
            </button>
        </div>
    `;

    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const uiDefault = document.getElementById('upload-ui-default');
    const uiSelected = document.getElementById('upload-ui-selected');
    const fileNameDisplay = document.getElementById('file-name');
    const uploadBtn = document.getElementById('upload-btn');
    const statusMsg = document.getElementById('status-message');
    const loadingOverlay = document.getElementById('upload-loading');

    let selectedFile = null;

    const updateUI = () => {
        if (selectedFile) {
            uiDefault.classList.add('hidden');
            uiSelected.classList.remove('hidden');
            fileNameDisplay.innerText = selectedFile.name;
            uploadBtn.disabled = false;
            uploadBtn.classList.remove('bg-slate-700', 'text-slate-400', 'cursor-not-allowed');
            uploadBtn.classList.add('bg-cyan-600', 'hover:bg-cyan-500', 'text-white', 'cursor-pointer');
            statusMsg.innerText = '';
        } else {
            uiDefault.classList.remove('hidden');
            uiSelected.classList.add('hidden');
            uploadBtn.disabled = true;
            uploadBtn.classList.add('bg-slate-700', 'text-slate-400', 'cursor-not-allowed');
            uploadBtn.classList.remove('bg-cyan-600', 'hover:bg-cyan-500', 'text-white', 'cursor-pointer');
        }
    };

    dropZone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            selectedFile = e.target.files[0];
            updateUI();
        }
    });
    // Drag events omitted for brevity, add if needed (standard boilerplate)

    uploadBtn.addEventListener('click', async (e) => {
        e.stopPropagation(); 
        if (!selectedFile) return;

        loadingOverlay.classList.remove('hidden');
        statusMsg.innerText = '';
        uploadBtn.disabled = true;

        try {
            const formData = new FormData();
            formData.append('file', selectedFile);

            await apiCall('/admin/import', { method: 'POST', body: formData });

            loadingOverlay.classList.add('hidden');
            statusMsg.innerHTML = '<span class="text-green-400">Upload Successful!</span>';
            setTimeout(() => navigateTo('search'), 1500);

        } catch (error) {
            loadingOverlay.classList.add('hidden');
            uploadBtn.disabled = false;
            statusMsg.innerHTML = `<span class="text-red-400">Error: ${error.message}</span>`;
        }
    });
}

// --- PROFILE LOGIC (Create/Edit/View) ---

async function loadOwnProfile(container) {
    const profile = await apiCall('/profile/me');
    if (profile) {
        userProfileCache = profile;
        isCreatingProfile = false;
        renderProfileView(container, profile, true);
    } else {
        isCreatingProfile = true;
        renderProfileEdit(container, {}, true);
    }
}

function renderProfileView(container, profile, isOwnProfile) {
    const fullName = `${profile.first_name || ''} ${profile.last_name || ''}`.trim();
    const majors = profile.major ? profile.major.split(',') : ['General Science'];
    
    // ИСПРАВЛЕНИЕ: Проверяем, что хотя бы одно поле существует (не null и не undefined), чтобы
    // отобразить блок индексов, даже если все значения равны 0.
    const hasIndices = (
        (profile.citations_total !== undefined && profile.citations_total !== null) ||
        (profile.citations_recent !== undefined && profile.citations_recent !== null) ||
        (profile.h_index !== undefined && profile.h_index !== null) ||
        (profile.i10_index !== undefined && profile.i10_index !== null) ||
        (profile.publication_count !== undefined && profile.publication_count !== null)
    );
    
    const indicesHtml = hasIndices ? `
        <div class="flex gap-5 mt-4 py-3 border-t border-b border-slate-800 flex-wrap justify-center md:justify-start">
            ${(profile.citations_total !== undefined && profile.citations_total !== null) ? `<div class="text-center">
                <div class="text-xs text-slate-400 uppercase">Total Citations</div>
                <div class="font-bold text-cyan-300">${profile.citations_total}</div>
            </div>` : ''}
            ${(profile.citations_recent !== undefined && profile.citations_recent !== null) ? `<div class="text-center">
                <div class="text-xs text-slate-400 uppercase">Recent Citations</div>
                <div class="font-bold text-cyan-300">${profile.citations_recent}</div>
            </div>` : ''}
            ${(profile.h_index !== undefined && profile.h_index !== null) ? `<div class="text-center">
                <div class="text-xs text-slate-400 uppercase">h-index</div>
                <div class="font-bold text-cyan-300">${profile.h_index}</div>
            </div>` : ''}
            ${(profile.i10_index !== undefined && profile.i10_index !== null) ? `<div class="text-center">
                <div class="text-xs text-slate-400 uppercase">i10-index</div>
                <div class="font-bold text-cyan-300">${profile.i10_index}</div>
            </div>` : ''}
            ${(profile.publication_count !== undefined && profile.publication_count !== null) ? `<div class="text-center">
                <div class="text-xs text-slate-400 uppercase">Publications</div>
                <div class="font-bold text-cyan-300">${profile.publication_count}</div>
            </div>` : ''}
        </div>
    ` : '';

    // Контакты: показываем только заполненные необязательные поля
    const optionalIds = ['google_scholar_id','scopus_id','orcid','arxiv_name','semantic_scholar_id'];
    const optionalHtml = optionalIds.map(k => {
        if (profile[k]) {
            // Переводим только отображаемое имя
            const displayKey = k.replace(/_/g,' ').replace('scholar id', 'Scholar ID').replace('arxiv name', 'arXiv Name').replace('orcid', 'ORCID').replace('scopus id', 'Scopus ID').replace('semantic scholar id', 'Semantic Scholar ID');
            return `<p class="text-slate-300 text-sm"><strong>${displayKey}:</strong> ${profile[k]}</p>`;
        }
        return '';
    }).join('');

    container.innerHTML = `
        <div class="tech-card max-w-4xl mx-auto p-8 rounded-xl relative animate-fade-in">
            <div class="absolute top-0 right-0 p-4">
               ${isOwnProfile ? `
                   <button onclick="editMyProfile()" class="bg-cyan-900/50 border border-cyan-500/30 text-cyan-400 px-4 py-2 rounded hover:bg-cyan-800 transition-all flex items-center gap-2">
                       <i class="fa-solid fa-pen-to-square"></i> EDIT PROFILE
                   </button>
               ` : ''}
            </div>
            
            <div class="flex flex-col md:flex-row gap-8 items-center md:items-start border-b border-slate-800 pb-8 mb-8">
                <div class="w-32 h-32 rounded-full bg-slate-800 border-2 border-cyan-400 flex items-center justify-center shadow-[0_0_15px_rgba(34,211,238,0.3)]">
                    <span class="text-4xl font-bold text-cyan-400">${(fullName[0] || '?').toUpperCase()}</span>
                </div>
                <div class="flex-grow text-center md:text-left">
                    <h2 class="text-3xl font-bold orbitron-font mb-2">${fullName}</h2>
                    <div class="flex gap-2 justify-center md:justify-start flex-wrap mb-4">
                        ${majors.map(m => `<span class="px-2 py-1 bg-cyan-900/30 border border-cyan-500/30 rounded text-xs text-cyan-300">${m.trim()}</span>`).join('')}
                    </div>
                    ${indicesHtml} 
                </div>
            </div>
            
            <div class="bg-slate-900/50 p-6 rounded border border-slate-700">
                <h3 class="text-xs text-slate-500 mb-2 font-bold uppercase">Biography</h3>
                <p class="text-slate-300">${profile.bio || 'Biography not specified.'}</p>
            </div>
             <div class="mt-4 bg-slate-900/50 p-6 rounded border border-slate-700">
                <h3 class="text-xs text-slate-500 mb-2 font-bold uppercase">Contact Information</h3>
                <p class="text-slate-300 text-sm">Email: ${localStorage.getItem('username') || 'Hidden'}</p>
                <p class="text-slate-300 text-sm">University: ${profile.university || 'Not specified'}</p>
                ${optionalHtml}
            </div>
        </div>
    `;
}

window.editMyProfile = function() {
    isCreatingProfile = false;
    const container = document.getElementById('main-content');
    renderProfileEdit(container, userProfileCache || {}, false);
};

function renderProfileEdit(container, data, isNewUser) {
    const modeCreate = isNewUser !== undefined ? isNewUser : isCreatingProfile;
    
    majorTags = data.major ? data.major.split(',').map(s=>s.trim()).filter(s=>s) : [];

    container.innerHTML = `
        <div class="tech-card max-w-3xl mx-auto p-8 rounded-xl animate-fade-in">
            <h2 class="text-2xl orbitron-font mb-6 border-b border-slate-700 pb-4">
                ${modeCreate ? 'CREATE PROFILE' : 'EDIT PROFILE'}
            </h2>
            
            <form id="profile-form" onsubmit="handleProfileSave(event)" class="space-y-6">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label class="block text-xs text-cyan-400 mb-1 uppercase font-bold">First Name *</label>
                        <input type="text" name="first_name" value="${data.first_name || ''}" required 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 focus:border-cyan-400 outline-none text-white">
                    </div>
                    <div>
                        <label class="block text-xs text-cyan-400 mb-1 uppercase font-bold">Last Name *</label>
                        <input type="text" name="last_name" value="${data.last_name || ''}" required 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 focus:border-cyan-400 outline-none text-white">
                    </div>
                </div>

                <div>
                    <label class="block text-xs text-cyan-400 mb-1 uppercase font-bold">University *</label>
                    <input type="text" name="university" value="${data.university || ''}" required 
                        class="w-full bg-slate-900 border border-slate-700 rounded p-3 focus:border-cyan-400 outline-none text-white">
                </div>

                <div>
                    <label class="block text-xs text-cyan-400 mb-1 uppercase font-bold">Competencies (Press Enter to add) *</label>
                    <div class="w-full bg-slate-900 border border-slate-700 rounded p-3 focus-within:border-cyan-400 flex flex-wrap gap-2 items-center">
                        <div id="tags-container" class="flex flex-wrap gap-2"></div>
                        <input type="text" id="tag-input" class="bg-transparent outline-none flex-grow min-w-[150px] text-white" placeholder="e.g.: Machine Learning...">
                    </div>
                </div>

                <div>
                    <label class="block text-xs text-cyan-400 mb-1 uppercase font-bold">Bio *</label>
                    <textarea name="bio" required rows="4"
                        class="w-full bg-slate-900 border border-slate-700 rounded p-3 focus:border-cyan-400 outline-none text-white">${data.bio || ''}</textarea>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs text-slate-400 mb-1 uppercase">Google Scholar ID</label>
                        <input type="text" name="google_scholar_id" value="${data.google_scholar_id || ''}" 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 outline-none text-white">
                    </div>
                    <div>
                        <label class="block text-xs text-slate-400 mb-1 uppercase">Scopus ID</label>
                        <input type="text" name="scopus_id" value="${data.scopus_id || ''}" 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 outline-none text-white">
                    </div>
                    <div>
                        <label class="block text-xs text-slate-400 mb-1 uppercase">ORCID</label>
                        <input type="text" name="orcid" value="${data.orcid || ''}" 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 outline-none text-white">
                    </div>
                    <div>
                        <label class="block text-xs text-slate-400 mb-1 uppercase">arXiv Name</label>
                        <input type="text" name="arxiv_name" value="${data.arxiv_name || ''}" 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 outline-none text-white">
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-xs text-slate-400 mb-1 uppercase">Semantic Scholar ID</label>
                        <input type="text" name="semantic_scholar_id" value="${data.semantic_scholar_id || ''}" 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 outline-none text-white">
                    </div>
                </div>

                <div id="form-feedback" class="hidden p-3 rounded text-center text-sm font-bold"></div>

                <button type="submit" id="save-btn" class="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold py-3 rounded transition-all mt-6">
                    ${modeCreate ? 'CREATE AND PROCEED' : 'SAVE CHANGES'}
                </button>
            </form>
        </div>
    `;

    renderTags();
    const tagInput = document.getElementById('tag-input');
    tagInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            const val = tagInput.value.trim();
            if (val && !majorTags.includes(val)) {
                majorTags.push(val);
                renderTags();
                tagInput.value = '';
            }
        }
    });
}

function renderTags() {
    const container = document.getElementById('tags-container');
    container.innerHTML = majorTags.map((tag, index) => `
        <span class="bg-cyan-900 text-cyan-200 text-xs px-2 py-1 rounded flex items-center gap-2">
            ${tag}
            <i class="fa-solid fa-xmark cursor-pointer hover:text-white" onclick="removeTag(${index})"></i>
        </span>
    `).join('');
}

window.removeTag = function(index) {
    majorTags.splice(index, 1);
    renderTags();
};

window.handleProfileSave = async function(e) {
    e.preventDefault();
    const btn = document.getElementById('save-btn');
    const feedback = document.getElementById('form-feedback');
    const formData = new FormData(e.target);
    const formProps = Object.fromEntries(formData);

    if (majorTags.length === 0) {
        alert("Please specify at least one competency.");
        return;
    }
    formProps.major = majorTags.join(', ');

    // Clean optional fields
    const optional = ['google_scholar_id','scopus_id','orcid','arxiv_name','semantic_scholar_id'];
    optional.forEach(k => {
        if (!formProps[k] || formProps[k].trim() === '') {
            delete formProps[k];
        }
    });

    // UI Loading
    const originalText = btn.innerText;
    btn.disabled = true;
    btn.innerText = "SAVING...";
    
    // Determine method based on state
    const method = isCreatingProfile ? 'POST' : 'PATCH';
    
    try {
        const res = await apiCall('/profile/me', {
            method: method,
            body: JSON.stringify(formProps)
        });

        if (res) {
            feedback.innerText = "SUCCESSFULLY SAVED";
            feedback.className = "p-3 rounded text-center text-sm font-bold bg-green-900/30 text-green-400 border border-green-500/50 block";
            
            isCreatingProfile = false;
            
            setTimeout(() => {
                initDashboardUI(); 
            }, 800);
        } else {
            throw new Error('Failed to get response');
        }
    } catch (error) {
        feedback.innerText = "ERROR: " + (error.message || 'Error');
        feedback.className = "p-3 rounded text-center text-sm font-bold bg-red-900/30 text-red-400 border border-red-500/50 block";
        btn.disabled = false;
        btn.innerText = originalText;
    }
};

// --- NEW REQUEST LOGIC ---

function renderCreateRequest(container) {
    requestRoles = []; 

    container.innerHTML = `
        <div class="tech-card max-w-4xl mx-auto p-8 rounded-xl animate-fade-in">
            <h2 class="text-2xl orbitron-font mb-2 text-cyan-400"><i class="fa-solid fa-plus-circle mr-2"></i> NEW REQUEST</h2>
            <p class="text-slate-400 text-sm mb-6 border-b border-slate-700 pb-4">Create a request to find a team of researchers.</p>
            
            <form id="create-request-form" onsubmit="handleRequestSubmit(event)" class="space-y-6">
                
                <div>
                    <label class="block text-xs text-cyan-400 mb-1 uppercase font-bold">Request Title</label>
                    <input type="text" name="title" required placeholder="e.g.: Optimization team for convex problems..."
                        class="w-full bg-slate-900 border border-slate-700 rounded p-4 focus:border-cyan-400 outline-none text-white font-bold text-lg placeholder-slate-600">
                </div>

                <div>
                    <label class="block text-xs text-cyan-400 mb-1 uppercase font-bold">Task Description</label>
                    <textarea name="description" required rows="5" placeholder="Detailed description..."
                        class="w-full bg-slate-900 border border-slate-700 rounded p-4 focus:border-cyan-400 outline-none text-white leading-relaxed placeholder-slate-600"></textarea>
                </div>

                <div class="bg-slate-900/50 p-4 rounded border border-slate-700">
                    <label class="block text-xs text-cyan-400 mb-3 uppercase font-bold flex justify-between items-center">
                        <span>Required Roles</span>
                    </label>

                    <div id="request-roles-container" class="space-y-3 mb-4">
                        <div class="text-center text-slate-600 text-sm italic py-4" id="no-roles-msg">Roles have not been added yet</div>
                    </div>

                    <div class="flex gap-2">
                        <input type="text" id="role-input" class="flex-grow bg-slate-900 border border-slate-600 rounded p-2 text-white text-sm" placeholder="e.g.: Python Backend Dev">
                        <button type="button" onclick="addRequestRole()" class="bg-cyan-800 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-bold">
                            <i class="fa-solid fa-plus"></i> ADD ROLE
                        </button>
                    </div>
                </div>

                <div id="req-feedback" class="hidden"></div>

                <button type="submit" id="create-req-btn" class="w-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold py-4 rounded transition-all mt-4">
                    PUBLISH REQUEST
                </button>
            </form>
        </div>
    `;
}

window.addRequestRole = function() {
    const input = document.getElementById('role-input');
    const val = input.value.trim();
    if (val) {
        requestRoles.push(val);
        input.value = '';
        renderRequestRoles();
    }
};

window.removeRequestRole = function(index) {
    requestRoles.splice(index, 1);
    renderRequestRoles();
};

function renderRequestRoles() {
    const container = document.getElementById('request-roles-container');
    const noRolesMsg = document.getElementById('no-roles-msg');
    
    if (requestRoles.length > 0) {
        if(noRolesMsg) noRolesMsg.style.display = 'none';
        container.innerHTML = requestRoles.map((role, index) => `
            <div class="bg-slate-800 border border-slate-600 p-3 rounded flex justify-between items-center animate-fade-in">
                <div class="flex items-center gap-3">
                    <span class="text-white text-sm">${role}</span>
                </div>
                <button type="button" onclick="removeRequestRole(${index})" class="text-red-400 hover:text-red-200 px-2">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<div class="text-center text-slate-600 text-sm italic py-4" id="no-roles-msg">No roles added</div>';
    }
}

window.handleRequestSubmit = async function(e) {
    e.preventDefault();
    const btn = document.getElementById('create-req-btn');
    const feedback = document.getElementById('req-feedback');
    const formData = new FormData(e.target);
    
    if (requestRoles.length === 0) {
        alert("Please add at least one required role.");
        return;
    }

    const payload = {
        title: formData.get('title'),
        description: formData.get('description'),
        required_roles: requestRoles
    };

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> CREATING...';

    try {
        // Assume endpoints /requests exists for example purposes
        const result = await apiCall('/requests', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (result) {
            container = document.getElementById('main-content');
            container.innerHTML = '<div class="text-center text-green-400 text-2xl mt-10">Request Created!</div>';
        } 
    } catch (error) {
        feedback.innerText = "ERROR: " + error.message;
        feedback.className = "block p-3 bg-red-900/50 text-red-200 border border-red-500 rounded text-center mb-4";
        btn.disabled = false;
        btn.innerText = 'PUBLISH REQUEST';
    }
};

// --- FEED & SEARCH RENDERERS ---

function renderFeed(container) {
    const feed = getMockFeed();
    container.innerHTML = `
        <h2 class="text-2xl orbitron-font mb-6 text-left border-b border-slate-800 pb-2">
            <i class="fa-solid fa-satellite-dish text-cyan-400 mr-2"></i> REQUEST FEED
        </h2>
        <div class="flex flex-col gap-4">
            ${feed.map(item => `
                <div class="tech-card p-6 rounded-xl flex flex-col md:flex-row gap-6 items-start md:items-center hover:bg-slate-900/80 transition-colors">
                    <div class="flex-grow">
                        <h3 class="text-xl font-bold text-white mb-1">${item.title}</h3>
                        <p class="text-slate-300 text-sm mb-3">${item.desc}</p>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderUserSearch(container) {
    container.innerHTML = `
        <h2 class="text-2xl orbitron-font mb-6"><i class="fa-solid fa-users text-cyan-400 mr-2"></i> SCIENTIST SEARCH</h2>
        <div class="mb-6 flex gap-4">
            <input type="text" id="search-input" placeholder="Enter name, university, or skill..." class="w-full bg-slate-900 p-4 rounded text-white border border-slate-700 focus:border-cyan-400 outline-none">
            <button onclick="handleUserSearch(document.getElementById('search-input').value)" class="bg-cyan-800 hover:bg-cyan-700 px-8 rounded text-white font-bold transition-all">SEARCH</button>
        </div>
        <div id="search-results-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        </div>
    `;
}

async function handleUserSearch(query) {
    const grid = document.getElementById('search-results-grid');
    grid.innerHTML = '<div class="col-span-full text-center text-cyan-400"><i class="fa-solid fa-circle-notch fa-spin"></i> Searching...</div>';
    
    try {
        const data = await apiCall(`/profile/search?q=${encodeURIComponent(query)}&limit=10`);
        
        if(!data || !data.length) { 
            grid.innerHTML = '<div class="col-span-full text-center text-slate-500">No results found.</div>'; 
            return; 
        }
        
        grid.innerHTML = data.map(p => `
            <div class="tech-card p-5 rounded hover:border-cyan-500/50 transition-all group cursor-pointer relative overflow-hidden" onclick="viewUser(${p.user_id})">
                <div class="flex items-center gap-4 mb-3">
                    <div class="w-10 h-10 rounded-full bg-slate-800 border border-cyan-500/30 flex items-center justify-center font-bold text-cyan-400">
                        ${(p.first_name || 'U')[0]}
                    </div>
                    <div>
                        <div class="font-bold text-white group-hover:text-cyan-300 transition-colors">${p.first_name} ${p.last_name}</div>
                        <div class="text-xs text-slate-500 truncate w-40">${p.university || 'University'}</div>
                    </div>
                </div>
                <div class="text-xs text-slate-400 bg-slate-900/50 p-2 rounded border border-slate-800">
                    ${p.major || 'Science'}
                </div>
            </div>
        `).join('');
    } catch (e) {
        grid.innerHTML = '<div class="col-span-full text-center text-red-400">Search error</div>';
    }
}

window.viewUser = async function(id) {
    const container = document.getElementById('main-content');
    container.innerHTML = '<div class="text-center mt-20"><i class="fa-solid fa-circle-notch fa-spin text-4xl text-cyan-400"></i></div>';
    const profile = await apiCall(`/profile/${id}`);
    if(profile) renderProfileView(container, profile, false);
    else container.innerHTML = '<div class="text-center text-red-400 mt-10">User not found</div>';
};

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    initDashboardUI();
});