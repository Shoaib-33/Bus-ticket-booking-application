// ===== Backend Status Check =====
async function checkStatus() {
    const dot = document.getElementById('statusDot');
    if (!dot) return;
    try {
        const res = await fetch('/stats', { signal: AbortSignal.timeout(2000) });
        if (res.ok) {
            dot.classList.add('online');
            dot.classList.remove('offline');
            dot.title = 'Backend connected';
        } else {
            throw new Error();
        }
    } catch {
        dot.classList.add('offline');
        dot.classList.remove('online');
        dot.title = 'Backend offline';
    }
}
checkStatus();

// ===== Toast Notifications =====
function showToast(message, type = 'success') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.transition = 'opacity 0.3s';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
