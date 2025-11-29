/*
 * dashboard-logic.js — обновлённая версия
 * Что сделано (кратко):
 * - Добавлены поля в форму профиля: google_scholar_id, scopus_id, orcid, arxiv_name, semantic_scholar_id (все необязательные)
 * - При сохранении пустые необязательные поля удаляются из payload ("не учитываются")
 * - Исправлено поведение при 401: для запроса /profile/me теперь не делается немедленный редирект на login (нужно позволить обработать ситуацию в UI)
 * - Добавлены индексы рядом с аватаркой (если в профиле присутствуют поля citations, h_index, i10_index)
 * - Кнопка РЕДАКТИРОВАТЬ теперь корректно открывает форму редактирования (PATCH), поведения не создаёт новый профиль
 * - Небольшие улучшения UX (статусы сохранения, валидация компетенций остаётся)
 */

// --- GLOBAL VARIABLES ---
let currentUserRole = 'guest';
let currentTab = 'home';
let userProfileCache = null; 
let majorTags = []; // Теги для профиля
let requestRoles = []; // Теги/Роли для создания заявки
let isCreatingProfile = false; // Флаг: true = новый юзер (POST), false = старый (PATCH)
const API_BASE_URL = 'http://localhost:8000/api/v1'; // Или полный путь: 'http://localhost:8000/api/v1'

// --- HELPERS ---

const getCookie = (name) => {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
};

const apiCall = async (endpoint, options = {}) => {
    const token = getCookie('access_token');
    const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...options.headers
    };

    if (token) headers['Authorization'] = `Bearer ${token}`;

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });

        // Если неавторизован
        if (response.status === 401) {
            // Для проверки профиля (/profile/me) мы не делаем автоматический редирект — пусть UI решит как поступить
            if (endpoint.includes('/profile/me')) {
                return null; // UI обработает создание/запрос профиля
            }
            // Для прочих эндпоинтов — стандартный редирект на логин
            window.location.href = 'login.html';
            return null;
        }

        // Если профиль не найден, возвращаем null (для обработки создания нового)
        if (response.status === 404 && endpoint.includes('/profile/me')) {
            return null;
        }

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'API request error');
        }

        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        if (!endpoint.includes('/profile/me')) {
            alert(error.message);
        }
        return null;
    }
};

// --- CORE FUNCTIONS ---

async function initDashboardUI() {
    // В реальном проекте эти данные берутся из localStorage или кук после логина
    const type = localStorage.getItem('userType'); 
    const email = localStorage.getItem('username');

    if (!type) {
        // window.location.href = 'login.html'; // Раскомментировать для продакшена
        console.warn("No user type found, proceeding as guest/dev");
    }

    updateHeaderUI(email, type);
    currentUserRole = (type === 'user') ? 'user' : 'guest';

    if (currentUserRole === 'user') {
        const loadingContainer = document.getElementById('main-content');
        if(loadingContainer) loadingContainer.innerHTML = '<div class="text-center mt-20"><i class="fa-solid fa-circle-notch fa-spin text-4xl text-cyan-400"></i><p class="mt-4 text-slate-400">Checking profile...</p></div>';

        const profile = await apiCall('/profile/me');

        if (!profile) {
            // Профиль не найден или не доступен -> Режим СОЗДАНИЯ (POST)
            console.log("Profile not found or not accessible - Initializing Creation Mode");
            isCreatingProfile = true;
            userProfileCache = null;
            renderNavigation(true); // Блокируем меню
            renderProfileEdit(document.getElementById('main-content'), {}, true);
        } else {
            // Профиль есть -> Режим РЕДАКТИРОВАНИЯ (PATCH)
            console.log("Profile found - Initializing Edit Mode");
            isCreatingProfile = false;
            userProfileCache = profile;
            renderNavigation(false); // Разблокируем меню
            navigateTo('home');
        }
    } else {
        renderNavigation(false);
        navigateTo('home');
    }
}

function updateHeaderUI(name, type) {
    const nameEl = document.getElementById('user-name');
    const roleEl = document.getElementById('user-role');
    
    if(nameEl) nameEl.innerText = userProfileCache ? `${userProfileCache.first_name || ''} ${userProfileCache.last_name || ''}`.trim() : (name || 'User');
    
    if(roleEl) {
        if (type === 'user') {
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
        nav.innerHTML = '<span class="text-slate-500 text-sm italic p-2">Fill in your profile to access the menu</span>';
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

    // Меню для ученого
    createBtn('home', 'fa-list-check', 'FEED', () => navigateTo('home'));
    createBtn('create', 'fa-plus', 'NEW REQUEST', () => navigateTo('create'));
    createBtn('search', 'fa-users', 'SEARCH', () => navigateTo('search'));
    createBtn('profile', 'fa-id-card', 'PROFILE', () => navigateTo('profile'));
}

function navigateTo(tab) {
    currentTab = tab;
    const container = document.getElementById('main-content');
    if(!container) return;
    
    container.innerHTML = '';
    container.style.opacity = 0;

    // Обновляем состояние кнопок
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    const activeBtn = document.querySelector(`.nav-btn[data-id="${tab}"]`);
    if(activeBtn) activeBtn.classList.add('active');

    setTimeout(() => {
        switch (tab) {
            case 'home': renderFeed(container); break;
            case 'create': renderCreateRequest(container); break;
            case 'search': renderUserSearch(container); break;
            case 'profile': loadOwnProfile(container); break;
        }
        container.style.transition = 'opacity 0.3s';
        container.style.opacity = 1;
    }, 100);
}

// --- 1. PROFILE LOGIC (POST vs PATCH FIX) ---

async function loadOwnProfile(container) {
    const profile = await apiCall('/profile/me');
    if (profile) {
        userProfileCache = profile;
        isCreatingProfile = false; // Если загрузили, значит он существует
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
    // При нажатии кнопки редактирования мы точно не создаем нового
    isCreatingProfile = false;
    const container = document.getElementById('main-content');
    renderProfileEdit(container, userProfileCache || {}, false);
};

function renderProfileEdit(container, data, isNewUser) {
    // Если isNewUser передан явно (при инициализации), используем его, иначе полагаемся на глобальный флаг
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
                        <label class="block text-xs text-slate-400 mb-1 uppercase">Google Scholar ID (Optional)</label>
                        <input type="text" name="google_scholar_id" value="${data.google_scholar_id || ''}" 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 outline-none text-white" placeholder="e.g.: _abcd1234">
                    </div>
                    <div>
                        <label class="block text-xs text-slate-400 mb-1 uppercase">Scopus ID (Optional)</label>
                        <input type="text" name="scopus_id" value="${data.scopus_id || ''}" 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 outline-none text-white" placeholder="e.g.: 1234567890">
                    </div>
                    <div>
                        <label class="block text-xs text-slate-400 mb-1 uppercase">ORCID (Optional)</label>
                        <input type="text" name="orcid" value="${data.orcid || ''}" 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 outline-none text-white" placeholder="e.g.: 0000-0002-1825-0097">
                    </div>
                    <div>
                        <label class="block text-xs text-slate-400 mb-1 uppercase">arXiv Name (Optional)</label>
                        <input type="text" name="arxiv_name" value="${data.arxiv_name || ''}" 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 outline-none text-white" placeholder="e.g.: username or handle">
                    </div>
                    <div class="md:col-span-2">
                        <label class="block text-xs text-slate-400 mb-1 uppercase">Semantic Scholar ID (Optional)</label>
                        <input type="text" name="semantic_scholar_id" value="${data.semantic_scholar_id || ''}" 
                            class="w-full bg-slate-900 border border-slate-700 rounded p-3 outline-none text-white" placeholder="e.g.: W:abcdef">
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

    // Убираем из payload пустые необязательные поля (чтобы "не учитывались")
    const optional = ['google_scholar_id','scopus_id','orcid','arxiv_name','semantic_scholar_id'];
    optional.forEach(k => {
        if (formProps[k] === undefined || formProps[k] === null || (typeof formProps[k] === 'string' && formProps[k].trim() === '')) {
            delete formProps[k];
        }
    });

    // UI Loading
    const originalText = btn.innerText;
    btn.disabled = true;
    btn.innerText = "SAVING...";
    
    // ОПРЕДЕЛЯЕМ МЕТОД: POST если isCreatingProfile true, иначе PATCH
    const method = isCreatingProfile ? 'POST' : 'PATCH';
    
    try {
        const res = await apiCall('/profile/me', {
            method: method,
            body: JSON.stringify(formProps)
        });

        if (res) {
            feedback.innerText = "SUCCESSFULLY SAVED";
            feedback.className = "p-3 rounded text-center text-sm font-bold bg-green-900/30 text-green-400 border border-green-500/50 block";
            
            // Если мы создали профиль, в следующий раз мы его обновляем
            isCreatingProfile = false;
            
            setTimeout(() => {
                initDashboardUI(); // Перезагружаем UI
            }, 800);
        } else {
            throw new Error('Failed to get response from server');
        }
    } catch (error) {
        feedback.innerText = "ERROR: " + (error.message || 'Error');
        feedback.className = "p-3 rounded text-center text-sm font-bold bg-red-900/30 text-red-400 border border-red-500/50 block";
        btn.disabled = false;
        btn.innerText = originalText;
    }
};


// --- 2. NEW REQUEST LOGIC ---

function renderCreateRequest(container) {
    requestRoles = []; // Сброс ролей при открытии формы

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
                    <textarea name="description" required rows="5" placeholder="Detailed description of the task you want to solve..."
                        class="w-full bg-slate-900 border border-slate-700 rounded p-4 focus:border-cyan-400 outline-none text-white leading-relaxed placeholder-slate-600"></textarea>
                </div>

                <div class="bg-slate-900/50 p-4 rounded border border-slate-700">
                    <label class="block text-xs text-cyan-400 mb-3 uppercase font-bold flex justify-between items-center">
                        <span>Required Roles / Specialists</span>
                        <span class="text-[10px] text-slate-500">Add blocks for each role</span>
                    </label>

                    <div id="request-roles-container" class="space-y-3 mb-4">
                        <div class="text-center text-slate-600 text-sm italic py-4" id="no-roles-msg">Roles have not been added yet</div>
                    </div>

                    <div class="flex gap-2">
                        <input type="text" id="role-input" class="flex-grow bg-slate-900 border border-slate-600 rounded p-2 text-white text-sm" placeholder="Describe the role (e.g.: Python Backend Dev with ML exp)">
                        <button type="button" onclick="addRequestRole()" class="bg-cyan-800 hover:bg-cyan-700 text-white px-4 py-2 rounded text-sm font-bold">
                            <i class="fa-solid fa-plus"></i> ADD ROLE
                        </button>
                    </div>
                </div>

                <div id="req-feedback" class="hidden"></div>

                <button type="submit" id="create-req-btn" class="w-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-bold py-4 rounded shadow-[0_0_20px_rgba(6,182,212,0.3)] transition-all transform hover:scale-[1.01] mt-4">
                    PUBLISH REQUEST
                </button>
            </form>
        </div>
    `;
}

// Управление ролями в заявке
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
                    <div class="w-8 h-8 rounded-full bg-cyan-900/50 flex items-center justify-center text-cyan-400 font-bold text-xs">
                        ${index + 1}
                    </div>
                    <span class="text-white text-sm">${role}</span>
                </div>
                <button type="button" onclick="removeRequestRole(${index})" class="text-red-400 hover:text-red-200 px-2">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `).join('');
    } else {
        container.innerHTML = '<div class="text-center text-slate-600 text-sm italic py-4" id="no-roles-msg">Roles have not been added yet</div>';
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
        const result = await apiCall('/requests', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (result) {
            renderRequestSuccess(result);
        } else {
            throw new Error("Failed to create request");
        }

    } catch (error) {
        feedback.innerText = "ERROR: " + error.message;
        feedback.className = "block p-3 bg-red-900/50 text-red-200 border border-red-500 rounded text-center font-bold mb-4";
        btn.disabled = false;
        btn.innerText = 'PUBLISH REQUEST';
    }
};

function renderRequestSuccess(data) {
    const container = document.getElementById('main-content');
    
    // Формируем блоки ролей для отображения
    const rolesHtml = data.required_roles.map((role, idx) => `
        <div class="bg-slate-900 border border-green-500/30 p-4 rounded-lg flex items-center gap-4">
            <div class="w-10 h-10 rounded bg-green-900/30 flex items-center justify-center text-green-400 border border-green-500/30">
                <i class="fa-solid fa-user-tag"></i>
            </div>
            <div>
                <div class="text-xs text-green-600 uppercase font-bold">Role #${idx + 1}</div>
                <div class="text-white font-medium">${role}</div>
            </div>
        </div>
    `).join('');

    container.innerHTML = `
        <div class="max-w-4xl mx-auto animate-fade-in">
            <div class="bg-green-900/20 border border-green-500 text-green-400 p-6 rounded-xl text-center mb-8 shadow-[0_0_20px_rgba(34,197,94,0.1)]">
                <i class="fa-solid fa-check-circle text-5xl mb-4"></i>
                <h2 class="text-2xl orbitron-font font-bold">REQUEST SUCCESSFULLY CREATED!</h2>
                <p class="text-green-300/80 mt-2">Your request has been published and is available for search.</p>
            </div>

            <div class="tech-card p-8 rounded-xl relative overflow-hidden">
                <div class="absolute top-0 left-0 w-1 h-full bg-green-500"></div>
                
                <h1 class="text-3xl font-bold text-white mb-4 orbitron-font">${data.title}</h1>
                
                <div class="bg-slate-900/50 p-6 rounded border border-slate-700 mb-6">
                    <h3 class="text-xs text-slate-500 mb-2 font-bold uppercase">Task Description</h3>
                    <p class="text-slate-300 leading-relaxed">${data.description}</p>
                </div>

                <h3 class="text-sm text-cyan-400 mb-4 font-bold uppercase border-b border-slate-700 pb-2">
                    <i class="fa-solid fa-users-viewfinder mr-2"></i> Seeking Specialists (Roles)
                </h3>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                    ${rolesHtml}
                </div>

                <div class="flex gap-4">
                    <button onclick="navigateTo('create')" class="flex-1 bg-slate-800 hover:bg-slate-700 text-white py-3 rounded border border-slate-600 transition-all font-bold">
                        <i class="fa-solid fa-plus mr-2"></i> CREATE ANOTHER
                    </button>
                    <button onclick="navigateTo('search')" class="flex-1 bg-gradient-to-r from-green-700 to-emerald-700 hover:from-green-600 hover:to-emerald-600 text-white py-3 rounded shadow-lg transition-all font-bold">
                        <i class="fa-solid fa-magnifying-glass mr-2"></i> FIND CANDIDATES
                    </button>
                </div>
            </div>
        </div>
    `;
}

// --- OTHER RENDERERS (FEED, SEARCH) ---

function renderFeed(container) {
    container.innerHTML = `
        <h2 class="text-2xl orbitron-font mb-6"><i class="fa-solid fa-satellite-dish text-cyan-400 mr-2"></i> REQUEST FEED</h2>
        <div class="tech-card p-6 rounded text-center text-slate-500">
            No active requests to display.
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
    
    // Имитация задержки и ответа, если сервер не отвечает реально
    try {
        const data = await apiCall(`/profile/search?q=${encodeURIComponent(query)}&limit=10`);
        
        if(!data || !data.length) { 
            grid.innerHTML = '<div class="col-span-full text-center text-slate-500">No results found.</div>'; 
            return; 
        }
        
        grid.innerHTML = data.map(p => `
            <div class="tech-card p-5 rounded hover:border-cyan-500/50 transition-all group cursor-pointer relative overflow-hidden" onclick="viewUser(${p.user_id})">
                <div class="absolute top-0 left-0 w-1 h-full bg-cyan-900 group-hover:bg-cyan-400 transition-colors"></div>
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