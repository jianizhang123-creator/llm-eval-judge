/**
 * Right panel — quality metrics dashboard, accuracy bars, error type
 * distribution, patterns, and prompt insights.
 */

function renderDashboard(stats) {
    document.getElementById('statTotal').textContent = stats.total_evaluated || 0;
    document.getElementById('statErrors').textContent = stats.error_count || 0;
    document.getElementById('statPrefs').textContent = stats.preference_count || 0;
    document.getElementById('statHalluc').textContent = ((stats.hallucination_rate || 0) * 100).toFixed(1) + '%';

    const acc = stats.accuracy_by_field || {};
    document.getElementById('accBars').innerHTML = Object.entries(acc).map(([field, val]) => {
        const pct = (val * 100).toFixed(1);
        const cls = val >= 0.9 ? 'high' : val >= 0.8 ? 'medium' : 'low';
        return `<div class="acc-row">
            <span class="acc-label">${field}</span>
            <div class="acc-track"><div class="acc-fill ${cls}" style="width:${pct}%"></div></div>
            <span class="acc-value">${pct}%</span>
        </div>`;
    }).join('');

    const dist = stats.error_type_distribution || {};
    document.getElementById('errorDist').innerHTML = Object.entries(dist).map(([type, count]) => {
        const color = ERROR_TYPE_COLORS[type] || '#94a3b8';
        const label = type.replace(/_/g, ' ');
        return `<div class="dist-row">
            <span class="dist-dot" style="background:${color}"></span>
            <span class="dist-name">${label}</span>
            <span class="dist-count">${count}</span>
        </div>`;
    }).join('') || '<span style="font-size:11px;color:var(--text-tertiary)">No data yet</span>';

    document.getElementById('statsGrid').classList.add('flash');
    setTimeout(() => document.getElementById('statsGrid').classList.remove('flash'), 500);
}

function renderPatterns(patterns) {
    const el = document.getElementById('patternsPanel');
    if (!patterns.length) { el.innerHTML = '<span style="font-size:11px;color:var(--text-tertiary)">Run analysis to discover patterns</span>'; return; }
    el.innerHTML = patterns.map(p => `
        <div class="pattern-card">
            <div class="pattern-name">${p.pattern_name || p.pattern}</div>
            <div class="pattern-desc">${p.description}</div>
            <div class="pattern-meta">Frequency: ${p.frequency} | Fields: ${(p.affected_fields || [p.affected_field]).join(', ')}</div>
        </div>
    `).join('');
}

function renderInsights(insights) {
    const el = document.getElementById('insightsPanel');
    if (!insights.length) { el.innerHTML = '<span style="font-size:11px;color:var(--text-tertiary)">No insights yet</span>'; return; }
    el.innerHTML = insights.map(i => `
        <div class="insight-card">
            <div class="insight-target">${i.target_field}</div>
            <div class="insight-issue">${i.issue}</div>
            <div class="insight-suggestion">${i.suggestion}</div>
            <span class="insight-priority priority-${i.priority}">${i.priority}</span>
        </div>
    `).join('');
}
