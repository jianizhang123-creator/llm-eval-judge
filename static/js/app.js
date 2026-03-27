/**
 * Main application entry — global state, constants, status management,
 * and initialisation.
 */

const state = { samples: [], knowledge: null, running: false };

const ERROR_TYPE_COLORS = {
    parsing_error: '#ef4444',
    classification_error: '#f59e0b',
    inference_error: '#3b82f6',
    hallucination: '#8b5cf6',
    context_missing: '#64748b'
};

function setStatus(status, text) {
    const dot = document.getElementById('statusDot');
    dot.style.background = status === 'running' ? 'var(--warning)' : status === 'error' ? 'var(--danger)' : 'var(--success)';
    document.getElementById('statusText').textContent = text;
}

// Initialise
document.addEventListener('DOMContentLoaded', async () => {
    await loadPresets();
    await loadDashboard();
    await loadKnowledge();
});

async function loadPresets() {
    try {
        const res = await fetch('/api/presets');
        state.samples = await res.json();
        renderSampleList();
    } catch(e) { console.error(e); }
}

async function loadDashboard() {
    try {
        const res = await fetch('/api/dashboard');
        const stats = await res.json();
        renderDashboard(stats);
    } catch(e) { console.error(e); }
}

async function loadKnowledge() {
    try {
        const res = await fetch('/api/knowledge');
        state.knowledge = await res.json();
        renderPatterns(state.knowledge.patterns || []);
    } catch(e) { console.error(e); }
}
