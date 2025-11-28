/**
 * dashboard-logic.js
 * Управляет рендерингом интерфейса, навигацией и моковыми данными.
 */

// --- MOCK DATA GENERATORS ---

const getMockChartData = () => {
    // Данные для графиков
    return Array.from({ length: 12 }, () => Math.floor(Math.random() * 80) + 20);
};

const getMockUsers = (count = 8) => {
    const roles = ['Quantum Physicist', 'Bio-Engineer', 'Data Scientist', 'AI Architect', 'Cyber-Security'];
    const unis = ['MIT', 'Stanford', 'Bauman MSTU', 'MIPT', 'ITMO University'];
    
    return Array.from({ length: count }, (_, i) => ({
        id: i + 1,
        name: `Subject_${100 + i}`,
        realName: ['Alex Mercer', 'Sarah Connor', 'Gordon Freeman', 'Ada Lovelace', 'Neo'][i % 5] + ` ${i}`,
        role: roles[Math.floor(Math.random() * roles.length)],
        uni: unis[Math.floor(Math.random() * unis.length)],
        bio: 'Researching neural networks and quantum entanglement for potential synergetic applications.',
        avatarColor: `hsl(${Math.random() * 360}, 70%, 60%)`
    }));
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
        },
        {
            id: 3,
            title: "Terraforming Simulation",
            author: "Mars Initiative",
            desc: "Building a predictive model for atmosphere generation. Need data scientists.",
            tags: ["Data Science", "ML", "Ecology"],
            req: "Knowledge of Tensorflow and Climate models."
        }
    ];
};

// --- STATE MANAGEMENT ---

let currentUserRole = 'guest'; // 'admin', 'user', 'guest'
let currentTab = 'home';
let usersDb = getMockUsers(12); // Имитация базы данных

// --- CORE RENDER FUNCTIONS ---

function initDashboardUI() {
    // 1. Определяем роль из localStorage (установлено в logic.js)
    const type = localStorage.getItem('userType');
    const name = localStorage.getItem('username');

    if (!type) return; // logic.js перенаправит на логин

    // Определяем роль для логики
    if (name === 'admin' || name === 'Admin') {
        currentUserRole = 'admin';
    } else if (type === 'user') {
        currentUserRole = 'user';
    } else {
        currentUserRole = 'guest';
    }

    // Обновляем Header (аватар и роль уже обновляет logic.js, но мы можем доработать)
    renderNavigation();
    
    // Загружаем начальную вкладку
    navigateTo('home');
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

    // Общие для всех (или специфичные)
    if (currentUserRole === 'admin') {
        createBtn('home', 'fa-chart-line', 'ANALYTICS', () => navigateTo('home'));
        createBtn('upload', 'fa-file-csv', 'UPLOAD CSV', () => navigateTo('upload'));
        createBtn('search', 'fa-magnifying-glass', 'USER BASE', () => navigateTo('search'));
    } else if (currentUserRole === 'user') {
        createBtn('home', 'fa-list-check', 'REQUESTS FEED', () => navigateTo('home'));
        createBtn('create', 'fa-plus', 'NEW REQUEST', () => navigateTo('create'));
        createBtn('search', 'fa-users', 'FIND SCIENTISTS', () => navigateTo('search'));
        createBtn('profile', 'fa-id-card', 'MY PROFILE', () => navigateTo('profile'));
    } else {
        // Guest
        createBtn('home', 'fa-eye', 'PUBLIC FEED', () => navigateTo('home'));
        createBtn('search', 'fa-magnifying-glass', 'USER SEARCH', () => navigateTo('search'));
    }
}

function navigateTo(tab) {
    currentTab = tab;
    const container = document.getElementById('main-content');
    container.innerHTML = ''; // Очистка
    container.style.opacity = 0;

    setTimeout(() => {
        switch (tab) {
            case 'home':
                if (currentUserRole === 'admin') renderAdminDashboard(container);
                else renderFeed(container);
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
                renderProfile(container, localStorage.getItem('username'), true);
                break;
        }
        // Анимация появления
        container.style.transition = 'opacity 0.3s';
        container.style.opacity = 1;
    }, 100);
}

// --- TAB CONTENT RENDERERS ---

// 1. ADMIN DASHBOARD (Charts)
function renderAdminDashboard(container) {
    const data = getMockChartData();
    
    let html = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fade-in">
            <div class="tech-card p-6 rounded-xl">
                <h3 class="text-xl text-cyan-400 mb-4"><i class="fa-solid fa-signal mr-2"></i> SYSTEM ACTIVITY</h3>
                <div class="chart-container">
                    ${data.map(h => `<div class="chart-bar" style="height: ${h}%"></div>`).join('')}
                </div>
                <div class="flex justify-between text-xs text-slate-500 mt-2">
                    <span>00:00</span><span>12:00</span><span>23:59</span>
                </div>
            </div>

            <div class="tech-card p-6 rounded-xl flex flex-col justify-center">
                <h3 class="text-xl text-cyan-400 mb-4"><i class="fa-solid fa-globe mr-2"></i> DEMOGRAPHICS</h3>
                <div class="flex gap-4 items-center justify-center py-8">
                     <div class="w-32 h-32 rounded-full border-4 border-cyan-500 flex items-center justify-center shadow-[0_0_20px_#06b6d4]">
                        <span class="text-2xl font-bold">84%</span>
                     </div>
                     <div class="text-sm text-slate-300">
                        <div class="mb-2"><i class="fa-solid fa-circle text-cyan-500 text-[8px]"></i> Authorized</div>
                        <div><i class="fa-solid fa-circle text-slate-600 text-[8px]"></i> Guests</div>
                     </div>
                </div>
            </div>
            
            <div class="tech-card p-6 rounded-xl col-span-1 md:col-span-2">
                 <h3 class="text-xl text-cyan-400 mb-4"><i class="fa-solid fa-network-wired mr-2"></i> NETWORK LOAD</h3>
                 <svg viewBox="0 0 1000 200" class="w-full h-32 svg-chart">
                    <defs>
                        <linearGradient id="grad" x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style="stop-color:#22d3ee;stop-opacity:0.5" />
                            <stop offset="100%" style="stop-color:#22d3ee;stop-opacity:0" />
                        </linearGradient>
                    </defs>
                    <path fill="url(#grad)" stroke="#22d3ee" stroke-width="2" 
                    d="M0,150 Q100,100 200,140 T400,100 T600,150 T800,80 T1000,120 V200 H0 Z" />
                 </svg>
            </div>
        </div>
    `;
    container.innerHTML = html;
}

// 2. CSV UPLOAD (Admin)
function renderUpload(container) {
    container.innerHTML = `
        <div class="tech-card max-w-2xl mx-auto p-10 rounded-xl text-center">
            <h2 class="text-3xl font-bold mb-6">UPLOAD USER DATABASE</h2>
            <div class="border-2 border-dashed border-slate-600 hover:border-cyan-400 rounded-xl p-10 transition-colors cursor-pointer bg-slate-900/50">
                <i class="fa-solid fa-cloud-arrow-up text-6xl text-slate-500 mb-4"></i>
                <p class="text-lg">Drag & Drop CSV file here</p>
                <p class="text-sm text-slate-400 mt-2">or click to browse</p>
                <input type="file" class="hidden" id="csv-input">
            </div>
            <button class="mt-6 bg-cyan-600 hover:bg-cyan-500 text-white px-8 py-3 rounded font-bold orbitron-font transition-all">
                PROCESS DATA
            </button>
        </div>
    `;
}

// 3. USER SEARCH (All Roles)
function renderUserSearch(container) {
    const users = usersDb; // Mock data
    
    let html = `
        <div class="mb-6 flex gap-4">
            <input type="text" placeholder="Search by name, university or skills..." 
                class="w-full bg-slate-900/80 border border-slate-700 rounded-lg p-4 text-white focus:border-cyan-400 outline-none">
            <button class="bg-cyan-900/50 border border-cyan-500/50 text-cyan-400 px-6 rounded-lg hover:bg-cyan-900 transition-all">
                <i class="fa-solid fa-filter"></i>
            </button>
        </div>
        <div class="user-card-grid">
            ${users.map(u => `
                <div class="info-card p-4 rounded-xl flex flex-col gap-4 relative overflow-hidden group">
                    <div class="absolute top-0 left-0 w-1 h-full bg-cyan-500 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 rounded-full flex items-center justify-center text-slate-900 font-bold text-xl" style="background-color: ${u.avatarColor}">
                            ${u.realName[0]}
                        </div>
                        <div>
                            <h4 class="font-bold text-lg leading-tight">${u.realName}</h4>
                            <p class="text-xs text-cyan-400 uppercase tracking-widest">${u.role}</p>
                        </div>
                    </div>
                    <div class="text-sm text-slate-400 h-10 overflow-hidden text-ellipsis">
                        ${u.bio}
                    </div>
                    <div class="text-xs text-slate-500 flex items-center gap-2">
                         <i class="fa-solid fa-graduation-cap"></i> ${u.uni}
                    </div>
                    <button onclick="viewUser(${u.id})" class="mt-auto w-full py-2 border border-slate-600 rounded hover:bg-cyan-500/10 hover:border-cyan-400 text-sm transition-all">
                        VIEW PROFILE
                    </button>
                </div>
            `).join('')}
        </div>
    `;
    container.innerHTML = html;
}

// 4. FEED (User/Guest)
function renderFeed(container) {
    const feed = getMockFeed();
    
    let html = `
        <h2 class="text-2xl orbitron-font mb-6 text-left border-b border-slate-800 pb-2">
            <i class="fa-solid fa-satellite-dish text-cyan-400 mr-2"></i> CURRENT RESEARCH REQUESTS
        </h2>
        <div class="flex flex-col gap-4">
            ${feed.map(item => `
                <div class="tech-card p-6 rounded-xl flex flex-col md:flex-row gap-6 items-start md:items-center hover:bg-slate-900/80 transition-colors">
                    <div class="flex-grow">
                        <div class="flex justify-between items-start">
                            <h3 class="text-xl font-bold text-white mb-1">${item.title}</h3>
                            <span class="text-xs text-slate-500 bg-slate-900 px-2 py-1 rounded border border-slate-700">${item.author}</span>
                        </div>
                        <p class="text-slate-300 text-sm mb-3">${item.desc}</p>
                        <div class="flex gap-2 flex-wrap">
                            ${item.tags.map(t => `<span class="tag">${t}</span>`).join('')}
                        </div>
                        <div class="mt-3 text-xs text-cyan-600">
                            <i class="fa-solid fa-circle-exclamation mr-1"></i> ${item.req}
                        </div>
                    </div>
                    ${currentUserRole === 'user' ? `
                    <button class="whitespace-nowrap bg-cyan-600/20 border border-cyan-500 text-cyan-400 px-6 py-3 rounded hover:bg-cyan-600 hover:text-white transition-all font-bold text-sm">
                        APPLY
                    </button>
                    ` : ''}
                </div>
            `).join('')}
        </div>
    `;
    container.innerHTML = html;
}

// 5. PROFILE (View/Edit) & CREATE
function renderProfile(container, username, isEditable) {
    container.innerHTML = `
        <div class="tech-card max-w-3xl mx-auto p-8 rounded-xl relative">
            <div class="absolute top-0 right-0 p-4">
               ${isEditable ? '<button class="text-slate-500 hover:text-cyan-400"><i class="fa-solid fa-pen-to-square text-xl"></i></button>' : ''}
            </div>
            <div class="flex flex-col md:flex-row gap-8 items-center md:items-start">
                <div class="w-32 h-32 rounded-full bg-slate-800 border-2 border-cyan-400 flex items-center justify-center">
                    <i class="fa-solid fa-user-astronaut text-5xl text-cyan-400"></i>
                </div>
                <div class="flex-grow text-center md:text-left">
                    <h2 class="text-3xl font-bold orbitron-font mb-2">${username || 'Unknown User'}</h2>
                    <p class="text-cyan-500 tracking-widest uppercase text-sm mb-4">AUTHORIZED RESEARCHER</p>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-left">
                        <div class="bg-slate-900/50 p-3 rounded border border-slate-700">
                            <div class="text-xs text-slate-500">University</div>
                            <div>Moscow Institute of Physics and Technology</div>
                        </div>
                        <div class="bg-slate-900/50 p-3 rounded border border-slate-700">
                            <div class="text-xs text-slate-500">Major</div>
                            <div>Quantum Computing</div>
                        </div>
                        <div class="bg-slate-900/50 p-3 rounded border border-slate-700 col-span-1 md:col-span-2">
                            <div class="text-xs text-slate-500">Bio</div>
                            <div class="text-sm">Passionate about connecting AI with biological neural networks. looking for a team for Hackathon 2025.</div>
                        </div>
                    </div>
                </div>
            </div>
            ${currentUserRole === 'admin' ? `
            <div class="mt-8 pt-6 border-t border-slate-800 flex justify-end gap-4">
                <button class="text-red-400 border border-red-900/50 px-4 py-2 rounded hover:bg-red-900/20">BAN USER</button>
                <button class="bg-cyan-600 text-white px-6 py-2 rounded hover:bg-cyan-500">SAVE CHANGES</button>
            </div>
            ` : ''}
        </div>
    `;
}

function renderCreateRequest(container) {
    container.innerHTML = `
        <div class="tech-card max-w-2xl mx-auto p-8 rounded-xl">
            <h2 class="text-2xl orbitron-font mb-6 text-center">INITIALIZE TEAM REQUEST</h2>
            <div class="space-y-4">
                <div>
                    <label class="block text-xs text-slate-400 mb-1">PROJECT TITLE</label>
                    <input type="text" class="w-full bg-slate-900 border border-slate-700 p-3 rounded focus:border-cyan-400 outline-none text-white">
                </div>
                <div>
                    <label class="block text-xs text-slate-400 mb-1">DESCRIPTION</label>
                    <textarea rows="4" class="w-full bg-slate-900 border border-slate-700 p-3 rounded focus:border-cyan-400 outline-none text-white"></textarea>
                </div>
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs text-slate-400 mb-1">REQUIRED ROLE</label>
                        <select class="w-full bg-slate-900 border border-slate-700 p-3 rounded focus:border-cyan-400 outline-none text-white">
                            <option>Frontend Dev</option>
                            <option>Data Scientist</option>
                            <option>Physicist</option>
                        </select>
                    </div>
                    <div>
                        <label class="block text-xs text-slate-400 mb-1">DIFFICULTY</label>
                        <select class="w-full bg-slate-900 border border-slate-700 p-3 rounded focus:border-cyan-400 outline-none text-white">
                            <option>Hard Science</option>
                            <option>Software Eng</option>
                            <option>Hybrid</option>
                        </select>
                    </div>
                </div>
                <button class="w-full mt-4 btn-glow bg-cyan-600 text-white py-3 rounded font-bold">
                    PUBLISH TO MAINFRAME
                </button>
            </div>
        </div>
    `;
}

// --- ACTIONS ---

// Переход в профиль конкретного пользователя (для поиска)
function viewUser(id) {
    const user = usersDb.find(u => u.id === id);
    if (!user) return;
    
    const container = document.getElementById('main-content');
    // Мы рендерим профиль "только для чтения", если это не админ
    const canEdit = currentUserRole === 'admin';
    
    // Переиспользуем рендер профиля, подменяя данные
    // В реальном проекте здесь был бы fetch запрос
    renderProfile(container, user.realName, canEdit);
    
    // Визуально сбрасываем активную вкладку, так как мы "ушли" из поиска
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
}

// Клик по своему аватару
function navigateToProfile() {
    if (currentUserRole === 'guest') return;
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    // Ищем кнопку профиля если есть и активируем, или просто рендерим
    const profileBtn = document.querySelector('.nav-btn[data-id="profile"]');
    if (profileBtn) profileBtn.classList.add('active');
    
    navigateTo('profile');
}