const API_BASE = 'http://20.2.137.92:8000';

export async function runPipeline(companyName) {
    const res = await fetch(`${API_BASE}/run-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_name: companyName }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Error ${res.status}`);
    }
    return res.json();
}

export async function getReports(companyName) {
    const res = await fetch(`${API_BASE}/reports/${encodeURIComponent(companyName)}`);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
}

export async function getFeatures(companyName) {
    const res = await fetch(`${API_BASE}/features/${encodeURIComponent(companyName)}`);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
}

export async function getCompetitors() {
    const res = await fetch(`${API_BASE}/competitors`);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
}

export async function getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Error ${res.status}`);
    return res.json();
}
