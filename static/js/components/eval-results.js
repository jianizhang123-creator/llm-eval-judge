/**
 * Center panel — evaluation result rendering, batch evaluation, and
 * pattern analysis triggers.
 */

function renderEvalResult(cardId, sample, data) {
    const cls = data.classification || {};
    const ann = data.annotation || {};
    const verdict = cls.overall_verdict || 'unknown';
    const verdictCls = `verdict-${verdict === 'mixed' ? 'mixed' : verdict}`;
    const fields = ['amount', 'category', 'date', 'merchant'];
    const mods = {};
    (cls.modifications || []).forEach(m => { mods[m.field] = m; });

    const el = document.getElementById(cardId);
    el.innerHTML = `
        <div class="eval-header">
            <span class="input-text">${sample.input}</span>
            <span class="eval-verdict ${verdictCls}">${verdict}</span>
        </div>
        <div style="font-size:11px;color:var(--text-secondary);margin-bottom:10px">${cls.summary || ''}</div>
        <div class="field-grid">
            ${fields.map(f => {
                const pred = sample.prediction[f];
                const corr = sample.user_correction?.[f];
                const mod = mods[f];
                const fieldCls = !corr ? 'unchanged' : (mod?.type || 'unchanged');
                const typeBg = fieldCls === 'error' ? 'var(--danger-bg)' : fieldCls === 'preference' ? 'var(--info-bg)' : fieldCls === 'ambiguous' ? 'var(--warning-bg)' : 'var(--bg)';
                const typeColor = fieldCls === 'error' ? 'var(--danger)' : fieldCls === 'preference' ? 'var(--info)' : fieldCls === 'ambiguous' ? 'var(--warning)' : 'var(--text-tertiary)';
                return `<div class="field-card ${fieldCls}">
                    <div class="field-name">${f}</div>
                    <div class="field-predicted">${pred}</div>
                    ${corr !== undefined ? `<div class="field-corrected">&rarr; ${corr}</div>` : ''}
                    ${mod ? `<div class="field-type" style="background:${typeBg};color:${typeColor}">${mod.type} (${(mod.confidence*100).toFixed(0)}%)</div>` : ''}
                </div>`;
            }).join('')}
        </div>
        ${ann.annotations && ann.annotations.length ? `
            <div class="annotation-section">
                <div class="annotation-title">Error Annotations</div>
                ${ann.annotations.map(a => `
                    <div class="annotation-item">
                        <strong>${a.field}</strong> — <span style="color:${ERROR_TYPE_COLORS[a.error_type] || '#64748b'}">${a.error_type.replace(/_/g,' ')}</span> (${a.severity})
                        <div class="annotation-label">${a.description}</div>
                        ${a.root_cause ? `<div class="annotation-label"><em>Root cause:</em> ${a.root_cause}</div>` : ''}
                    </div>
                `).join('')}
            </div>
        ` : ''}
    `;
}

async function batchEvaluate() {
    if (state.running) return;
    state.running = true;
    setStatus('running', 'Batch evaluating...');
    document.getElementById('batchBtn').disabled = true;
    document.getElementById('welcomeState').style.display = 'none';
    const area = document.getElementById('resultsArea');
    area.style.display = 'block';
    area.innerHTML = `<div class="batch-progress" id="batchProgress">
        <strong>Batch Evaluation</strong>
        <div class="batch-bar"><div class="batch-fill" id="batchFill" style="width:0%"></div></div>
        <span style="font-size:11px;color:var(--text-secondary)" id="batchText">Starting...</span>
    </div>`;

    const handlers = {
        batch_progress: (d) => {
            const pct = (d.current / d.total * 100).toFixed(0);
            document.getElementById('batchFill').style.width = pct + '%';
            document.getElementById('batchText').textContent = `${d.current} / ${d.total} — ${d.sample_id}`;
        },
        sample_done: (d) => {
            const sample = state.samples.find(s => s.id === d.sample_id);
            if (sample && d.classification) {
                sample.eval_result = d.classification;
            }
            if (d.sample_id && d.classification?.overall_verdict !== 'correct') {
                const fakeSample = sample || { input: d.input || '', prediction: d.prediction || {}, user_correction: d.user_correction || {} };
                const cardId = `eval_batch_${d.sample_id}`;
                area.insertAdjacentHTML('beforeend', `<div class="eval-card" id="${cardId}"></div>`);
                renderEvalResult(cardId, fakeSample, d);
            }
        },
        dashboard_update: (d) => renderDashboard(d),
        batch_complete: (d) => {
            document.getElementById('batchFill').style.width = '100%';
            document.getElementById('batchText').textContent = `Complete — ${d.total || 0} samples evaluated`;
            renderSampleList();
        },
        error: () => {}
    };

    await streamSSE('/api/batch', { sample_ids: [] }, handlers);
    state.running = false;
    setStatus('ready', 'Batch complete');
    document.getElementById('batchBtn').disabled = false;
}

async function analyzePatterns() {
    if (state.running) return;
    state.running = true;
    setStatus('running', 'Analyzing patterns...');
    document.getElementById('analyzeBtn').disabled = true;

    document.getElementById('patternsPanel').innerHTML = '<span class="agent-mini running">Pattern Analysis running...</span>';
    document.getElementById('insightsPanel').innerHTML = '<span class="agent-mini running">Waiting...</span>';

    const handlers = {
        agent_start: (d) => {
            if (d.agent === 'pattern_analysis') document.getElementById('patternsPanel').innerHTML = '<span class="agent-mini running">Analyzing patterns...</span>';
            if (d.agent === 'prompt_insight') document.getElementById('insightsPanel').innerHTML = '<span class="agent-mini running">Generating insights...</span>';
        },
        agent_done: (d) => {
            if (d.agent === 'pattern_analysis' && d.result?.patterns) renderPatterns(d.result.patterns);
            if (d.agent === 'prompt_insight' && d.result?.insights) renderInsights(d.result.insights);
        },
        analysis_complete: () => {},
        error: () => {}
    };

    await streamSSE('/api/analyze', {}, handlers);
    state.running = false;
    setStatus('ready', 'Analysis complete');
    document.getElementById('analyzeBtn').disabled = false;
}
