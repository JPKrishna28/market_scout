import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { HiOutlinePlay, HiOutlineDocumentText, HiOutlineUserGroup, HiOutlineShieldCheck, HiOutlineClock, HiOutlineSparkles } from 'react-icons/hi';
import { getCompetitors, getHealth } from '../api';
import './Dashboard.css';

export default function Dashboard() {
    const [competitors, setCompetitors] = useState([]);
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        async function load() {
            try {
                const [compData, healthData] = await Promise.all([
                    getCompetitors().catch(() => []),
                    getHealth().catch(() => null),
                ]);
                setCompetitors(compData);
                setHealth(healthData);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    return (
        <div className="dashboard fade-in">
            <div className="page-header">
                <h1>Welcome to Market Scout</h1>
                <p>Your AI-powered competitive intelligence platform</p>
            </div>

            <div className="stats-grid stagger">
                <div className="stat-card fade-in-up">
                    <div className="stat-icon" style={{ background: 'var(--info-bg)', color: 'var(--info)' }}>
                        <HiOutlineUserGroup />
                    </div>
                    <div className="stat-info">
                        <h3>{loading ? '—' : competitors.length}</h3>
                        <p>Tracked Companies</p>
                    </div>
                </div>

                <div className="stat-card fade-in-up">
                    <div className="stat-icon" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}>
                        <HiOutlineShieldCheck />
                    </div>
                    <div className="stat-info">
                        <h3>{health ? 'Online' : '—'}</h3>
                        <p>System Status</p>
                    </div>
                </div>

                <div className="stat-card fade-in-up">
                    <div className="stat-icon" style={{ background: 'rgba(139, 92, 246, 0.12)', color: '#a78bfa' }}>
                        <HiOutlineSparkles />
                    </div>
                    <div className="stat-info">
                        <h3>LLaMA 3.3</h3>
                        <p>LLM Engine</p>
                    </div>
                </div>

                <div className="stat-card fade-in-up">
                    <div className="stat-icon" style={{ background: 'var(--warning-bg)', color: 'var(--warning)' }}>
                        <HiOutlineClock />
                    </div>
                    <div className="stat-info">
                        <h3>7 Days</h3>
                        <p>Recency Window</p>
                    </div>
                </div>
            </div>

            <div className="dashboard-grid">
                <div className="card quick-action fade-in-up" onClick={() => navigate('/run')}>
                    <div className="quick-action-icon run">
                        <HiOutlinePlay />
                    </div>
                    <div className="quick-action-content">
                        <h3>Run Intelligence Pipeline</h3>
                        <p>Enter a company name and generate a comprehensive technical feature report in seconds.</p>
                    </div>
                    <span className="quick-action-arrow">→</span>
                </div>

                <div className="card quick-action fade-in-up" onClick={() => navigate('/reports')}>
                    <div className="quick-action-icon reports">
                        <HiOutlineDocumentText />
                    </div>
                    <div className="quick-action-content">
                        <h3>View Historical Reports</h3>
                        <p>Browse past intelligence reports with executive summaries, confidence scores, and citations.</p>
                    </div>
                    <span className="quick-action-arrow">→</span>
                </div>

                <div className="card quick-action fade-in-up" onClick={() => navigate('/competitors')}>
                    <div className="quick-action-icon competitors">
                        <HiOutlineUserGroup />
                    </div>
                    <div className="quick-action-content">
                        <h3>Manage Competitors</h3>
                        <p>View and track the companies in your competitive landscape.</p>
                    </div>
                    <span className="quick-action-arrow">→</span>
                </div>
            </div>

            <div className="card pipeline-info fade-in-up">
                <h3>🔗 Pipeline Architecture</h3>
                <div className="pipeline-steps">
                    {[
                        { step: '1', label: 'Guardrails', desc: 'OWASP security checks' },
                        { step: '2', label: 'Search Planning', desc: 'LLM query generation' },
                        { step: '3', label: 'Web Search', desc: 'Tavily API execution' },
                        { step: '4', label: 'Smart Scraping', desc: '3-tier fallback cascade' },
                        { step: '5', label: 'Date Validation', desc: '7-day recency filter' },
                        { step: '6', label: 'Content Filter', desc: 'Technical relevance check' },
                        { step: '7', label: 'Authority Check', desc: 'Source credibility scoring' },
                        { step: '8', label: 'Feature Extraction', desc: 'Structured data extraction' },
                        { step: '9', label: 'Verification', desc: 'SBERT cross-source clustering' },
                        { step: '10', label: 'Scoring', desc: 'Multi-signal confidence' },
                        { step: '11', label: 'Synthesis', desc: 'Executive report generation' },
                    ].map((item, i) => (
                        <div key={i} className="pipeline-step">
                            <div className="step-number">{item.step}</div>
                            <div className="step-info">
                                <strong>{item.label}</strong>
                                <span>{item.desc}</span>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
