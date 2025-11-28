/**
 * bg-effects.js
 * Отвечает ТОЛЬКО за красивые частицы на фоне.
 */

const randomRange = (min, max) => Math.random() * (max - min) + min;

const createParticle = () => {
    const container = document.getElementById('tech-bg-container');
    if (!container) return;

    const particle = document.createElement('div');
    particle.className = 'particle';

    const size = randomRange(2, 6);
    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;
    particle.style.left = `${randomRange(0, 100)}%`;
    particle.style.bottom = `${randomRange(-5, -20)}%`;
    particle.style.animationDuration = `${randomRange(8, 15)}s`;
    particle.style.animationDelay = `-${randomRange(0, 15)}s`;

    container.appendChild(particle);
    
    // Удаляем частицу после завершения анимации, чтобы DOM не переполнялся
    setTimeout(() => {
        particle.remove();
    }, 15000);
};

const startParticleSystem = (count) => {
    for (let i = 0; i < count; i++) {
        createParticle();
    }
    setInterval(createParticle, 500); 
};

// Запуск при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    startParticleSystem(20);
});