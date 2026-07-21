/* Resume Optimizer — Client-side JS */

// Check Ollama status on load
document.addEventListener('DOMContentLoaded', () => {
    checkOllamaStatus();
});

function checkOllamaStatus() {
    const el = document.getElementById('ollama-status');
    if (!el) return;

    fetch('/api/ollama/status')
        .then(r => r.json())
        .then(data => {
            if (data.connected) {
                el.innerHTML = `<span class="dot dot-green"></span> Ollama connected`;
            } else {
                el.innerHTML = `<span class="dot dot-red"></span> Ollama offline`;
            }
        })
        .catch(() => {
            el.innerHTML = `<span class="dot dot-red"></span> Ollama offline`;
        });
}
