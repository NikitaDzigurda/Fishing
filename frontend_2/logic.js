/**
 * logic.js
 * Обновленная версия с проверкой регистрации.
 */
const API_BASE_URL = 'http://localhost:8000/api/v1'; // Или полный путь: 'http://localhost:8000/api/v1'

const MOCK_API_DELAY = 0; // 1.5 секунды задержка

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Функция установки куки
const setCookie = (name, value, days = 7) => {
    let expires = "";
    if (days) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        expires = "; expires=" + date.toUTCString();
    }
    // SameSite=Lax и path=/ обязательны для корректной работы
    document.cookie = name + "=" + (value || "") + expires + "; path=/; SameSite=Lax";
};

// Функция удаления куки
const deleteCookie = (name) => {
    document.cookie = name + '=; Path=/; Expires=Thu, 01 Jan 1970 00:00:01 GMT;';
};

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

const saveSession = (type, email, tokens = null) => {
    console.log(type, email, tokens);
    // Мета-данные пользователя храним в localStorage для удобства UI
    localStorage.setItem('userType', type);
    localStorage.setItem('username', email);

    // Токены сохраняем в Cookies
    if (tokens) {
        // access_token живет, например, 1 день
        setCookie('access_token', tokens.access_token, 1);

        // refresh_token живет дольше, например, 7 дней
        setCookie('refresh_token', tokens.refresh_token, 7);
    }
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

async function handleLogin() {
    const loginInput = document.getElementById('login-input'); // Email
    const passInput = document.getElementById('pass-input');
    const btn = document.getElementById('btn-login');

    let isValid = true;
    if (!loginInput.value.trim()) { showError(loginInput); isValid = false; }
    if (!passInput.value.trim()) { showError(passInput); isValid = false; }
    if (!isValid) return;

    setButtonLoading(btn, true);

    try {
        const payload = {
            email: loginInput.value.trim(),
            password: passInput.value.trim()
        };

        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const msg = errorData.detail
                ? (Array.isArray(errorData.detail) ? errorData.detail[0].msg : errorData.detail)
                : 'Ошибка входа.';
            throw new Error(msg);
        }

        const data = await response.json(); // { access_token, refresh_token, token_type }

        // Сохраняем в куки
        saveSession('user', payload.email, data);
        window.location.href = 'dashboard.html';

    } catch (error) {
        console.error('Login error:', error);
        alert(error.message);
        setButtonLoading(btn, false);
    }
}
// ... (Остальной код: delay, showError, setButtonLoading, initLogin и т.д.) ...

// Конфигурация API

// 3. РЕГИСТРАЦИЯ (С ЗАПРОСОМ К API)
async function handleRegister() {
    const loginInput = document.getElementById('reg-login');
    const passInput = document.getElementById('reg-pass');
    const btn = document.getElementById('btn-register');

    // 1. Валидация на клиенте
    let isValid = true;
    if (!loginInput.value.trim()) { showError(loginInput); isValid = false; }
    if (!passInput.value.trim()) { showError(passInput); isValid = false; }
    if (!isValid) return;

    // 2. Включаем загрузку
    setButtonLoading(btn, true);

    try {
        // Формируем данные
        const payload = {
            email: loginInput.value.trim(),
            password: passInput.value.trim()
        };

        // 3. Отправляем запрос
        // ВАЖНО: В вашем OpenAPI нет '/register'. Я добавил его как пример.
        // Если вы хотите использовать '/task', замените URL ниже.
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        console.log("repsonse");

        console.log(response);

        // 4. Обработка ошибок HTTP (например, 400 Bad Request, 409 Conflict)
        if (response.status !== 200) {
            // Пытаемся получить текст ошибки от сервера
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || errorData.message || 'Ошибка регистрации';

            throw new Error(errorMessage);
        }

        // 5. Успешная регистрация
        // Опционально: получаем ответ, если сервер возвращает ID пользователя
        // const data = await response.json(); 

        // Перенаправляем на логин с сообщением об успехе
        window.location.href = 'login.html?status=registered';

    } catch (error) {
        console.error('Registration failed:', error);

        // Показываем ошибку пользователю (можно сделать красивее, пока alert)
        alert(`Не удалось зарегистрироваться: ${error.message}`);

        // Сбрасываем кнопку, чтобы можно было попробовать снова
        setButtonLoading(btn, false);
    }
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