/**
 * logic.js
 * Обновленная версия с проверкой регистрации.
 */

const MOCK_API_DELAY = 1500; // 1.5 секунды задержка

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Показать ошибку
const showError = (inputElement) => {
    const parent = inputElement.parentElement;
    parent.classList.add('input-error');
    inputElement.addEventListener('input', () => {
        parent.classList.remove('input-error');
    }, { once: true });
};

// Состояние кнопки
const setButtonLoading = (btn, isLoading, originalText = '') => {
    const span = btn.querySelector('span');
    if (isLoading) {
        btn.disabled = true;
        btn.dataset.originalText = span.innerText;
        span.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> PROCESSING...';
    } else {
        btn.disabled = false;
        span.innerText = btn.dataset.originalText || originalText;
    }
};

const saveSession = (type, username) => {
    localStorage.setItem('userType', type);
    localStorage.setItem('username', username);
};

// --- ОСНОВНЫЕ ФУНКЦИИ ---

// 1. ПРОВЕРКА СООБЩЕНИЙ НА СТРАНИЦЕ ВХОДА (НОВАЯ ФУНКЦИЯ)
function initLogin() {
    // Проверяем параметры URL (например, login.html?status=registered)
    const params = new URLSearchParams(window.location.search);
    
    if (params.get('status') === 'registered') {
        const msgBox = document.getElementById('success-message');
        if (msgBox) {
            msgBox.classList.remove('hidden'); // Показываем сообщение
            msgBox.classList.add('flex'); // Для Flexbox верстки
        }
    }
}

// 2. ВХОД
async function handleLogin() {
    const loginInput = document.getElementById('login-input');
    const passInput = document.getElementById('pass-input');
    const btn = document.getElementById('btn-login');

    let isValid = true;
    if (!loginInput.value.trim()) { showError(loginInput); isValid = false; }
    if (!passInput.value.trim()) { showError(passInput); isValid = false; }
    if (!isValid) return;

    setButtonLoading(btn, true);
    await delay(MOCK_API_DELAY);

    saveSession('user', loginInput.value);
    window.location.href = 'dashboard.html';
}

// 3. РЕГИСТРАЦИЯ (ИЗМЕНЕНО)
async function handleRegister() {
    const loginInput = document.getElementById('reg-login');
    const passInput = document.getElementById('reg-pass');
    const btn = document.getElementById('btn-register');

    let isValid = true;
    if (!loginInput.value.trim()) { showError(loginInput); isValid = false; }
    if (!passInput.value.trim()) { showError(passInput); isValid = false; }
    if (!isValid) return;

    setButtonLoading(btn, true);
    await delay(MOCK_API_DELAY);

    // ВАЖНО: Мы НЕ сохраняем сессию здесь. Мы отправляем пользователя логиниться.
    // Передаем параметр status=registered
    window.location.href = 'login.html?status=registered';
}

// 4. ГОСТЕВОЙ РЕЖИМ
async function handleGuest() {
    const btn = document.getElementById('btn-guest');
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i>';
    await delay(800);
    saveSession('guest', 'Guest User');
    window.location.href = 'dashboard.html';
}

// 5. ДАШБОРД
function initDashboard() {
    const userType = localStorage.getItem('userType');
    const username = localStorage.getItem('username');

    if (!userType) {
        window.location.href = 'login.html';
        return;
    }

    const avatarEl = document.getElementById('user-avatar');
    const nameEl = document.getElementById('user-name');
    const roleEl = document.getElementById('user-role');
    const iconEl = avatarEl.querySelector('i');

    nameEl.innerText = username || 'Unknown';

    if (userType === 'user') {
        avatarEl.classList.add('avatar-user');
        iconEl.classList.add('fa-user-astronaut');
        roleEl.innerText = 'AUTHORIZED PARTICIPANT';
        roleEl.classList.add('text-cyan-400');
    } else {
        avatarEl.classList.add('avatar-guest');
        iconEl.classList.add('fa-user-secret');
        roleEl.innerText = 'GUEST ACCESS';
        roleEl.classList.add('text-slate-400');
    }
}

// 6. ВЫХОД
function handleLogout() {
    localStorage.clear();
    window.location.href = 'login.html';
}

// АВТОЗАПУСК ПРОВЕРКИ ПРИ ЗАГРУЗКЕ СТРАНИЦЫ
document.addEventListener('DOMContentLoaded', () => {
    // Если мы на странице логина, запускаем проверку сообщений
    if (document.getElementById('login-input')) {
        initLogin();
    }
});