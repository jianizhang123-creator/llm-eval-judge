/**
 * Left panel — sample list rendering and single/manual evaluation triggers.
 */

function renderSampleList() {
    const el = document.getElementById('sampleList');
    document.getElementById('sampleCount').textContent = state.samples.length;
    el.innerHTML = state.samples.map(s => {
        const hasCorr = s.user_correction && Object.keys(s.user_correction).length > 0;
        const verdict = s.eval_result?.overall_verdict;
        let cls = '';
        if (verdict === 'correct') cls = 'evaluated';
        else if (verdict === 'error') cls = 'has-error';
        else if (verdict === 'preference') cls = 'has-preference';
        else if (verdict === 'mixed') cls = 'has-error';
        const badgeCls = verdict ? `badge-${verdict === 'mixed' ? 'mixed' : verdict}` : 'badge-pending';
        const badgeText = verdict || (hasCorr ? 'pending' : 'no change');
        return `<div class="sample-item ${cls}" onclick="evaluateSample('${s.id}')">
            <div class="sample-input">${s.input}</div>
            <div class="sample-meta">
                <span class="sample-badge ${badgeCls}">${badgeText}</span>
                ${hasCorr ? `<span>modified: ${Object.keys(s.user_correction).join(', ')}</span>` : '<span>no modification</span>'}
            </div>
        </div>`;
    }).join('');
}

async function evaluateSample(sampleId) {
    if (state.running) return;
    const sample = state.samples.find(s => s.id === sampleId);
    if (!sample) return;
    if (!sample.user_correction || Object.keys(sample.user_correction).length === 0) return;

    state.running = true;
    setStatus('running', `Evaluating ${sampleId}...`);
    document.getElementById('welcomeState').style.display = 'none';
    const area = document.getElementById('resultsArea');
    area.style.display = 'block';

    const cardId = `eval_${sampleId}`;
    const cardHtml = `<div class="eval-card" id="${cardId}">
        <div class="eval-header">
            <span class="input-text">${sample.input}</span>
            <span class="agent-mini running" id="${cardId}_cls">Classification...</span>
        </div>
        <div id="${cardId}_content"><span style="font-size:11px;color:var(--text-tertiary)">Processing...</span></div>
    </div>`;
    area.insertAdjacentHTML('afterbegin', cardHtml);

    const handlers = {
        agent_start: (d) => {
            const el = document.getElementById(`${cardId}_cls`);
            if (el) { el.className = 'agent-mini running'; el.textContent = d.agent + '...'; }
        },
        agent_done: (d) => {
            const el = document.getElementById(`${cardId}_cls`);
            if (el) { el.className = 'agent-mini done'; el.textContent = d.agent + ' ✓'; }
        },
        eval_complete: (d) => {
            renderEvalResult(cardId, sample, d);
            sample.eval_result = d.classification;
            renderSampleList();
        },
        dashboard_update: (d) => renderDashboard(d),
        error: () => {}
    };

    await streamSSE('/api/evaluate', {
        sample_id: sampleId, input: sample.input,
        prediction: sample.prediction, user_correction: sample.user_correction
    }, handlers);

    state.running = false;
    setStatus('ready', 'Done');
}

async function manualEvaluate() {
    const input = document.getElementById('manualInput').value.trim();
    let pred, corr;
    try { pred = JSON.parse(document.getElementById('manualPred').value); } catch(e) { alert('Invalid prediction JSON'); return; }
    try { corr = JSON.parse(document.getElementById('manualCorr').value); } catch(e) { alert('Invalid correction JSON'); return; }
    if (!input) return;

    state.running = true;
    setStatus('running', 'Evaluating...');
    document.getElementById('welcomeState').style.display = 'none';
    const area = document.getElementById('resultsArea');
    area.style.display = 'block';

    const cardId = 'eval_manual_' + Date.now();
    area.insertAdjacentHTML('afterbegin', `<div class="eval-card" id="${cardId}">
        <div class="eval-header"><span class="input-text">${input}</span><span class="agent-mini running">Processing...</span></div>
        <div id="${cardId}_content"><span style="font-size:11px;color:var(--text-tertiary)">Processing...</span></div>
    </div>`);

    const fakeSample = { input, prediction: pred, user_correction: corr };
    const handlers = {
        agent_start: () => {},
        agent_done: () => {},
        eval_complete: (d) => renderEvalResult(cardId, fakeSample, d),
        dashboard_update: (d) => renderDashboard(d),
        error: () => {}
    };
    await streamSSE('/api/evaluate', { sample_id: 'manual', input, prediction: pred, user_correction: corr }, handlers);
    state.running = false;
    setStatus('ready', 'Done');
}
