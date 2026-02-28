import { useState } from 'react';
import { HiOutlinePlay, HiOutlineSparkles, HiOutlineExternalLink, HiOutlineShieldCheck, HiOutlineExclamationCircle } from 'react-icons/hi';
import { runPipeline } from '../api';
import './RunPipeline.css';

export default function RunPipeline() {
    const [company, setCompany] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState('');

    const handleRun = async (e) => {
        e.preventDefault();
        if (!company.trim()) return;
        setLoading(true);
        setError('');
        setResult(null);

        try {
            const data = await runPipeline(company.trim());
            setResult(data);
        } catch (err) {
            setError(err.message || 'Pipeline execution failed');
        } finally {
            setLoading(false);
        }
    };

    const report = result?.report || result;

    return (
        <div className="run-pipeline fade-in">
            <div className="page-header">
                <h1>Run Intelligence Pipeline</h1>
                <p>Enter a company name to discover their latest technical features from the past 7 days</p>
            </div>

            <form className="run-form card" onSubmit={handleRun}>
                <div className="form-row">
                    <div className="input-wrapper">
                        <HiOutlineSparkles className="input-icon" />
                        <input
                            type="text"
                            className="input pipeline-input"
                            placeholder="Enter company name (e.g. OpenAI, Google DeepMind, Anthropic)"
                            value={company}
                            onChange={e => setCompany(e.target.value)}
                            disabled={loading}
                            maxLength={200}
                        />
                    </div>
                    <button type="submit" className="btn btn-primary run-btn" disabled={loading || !company.trim()}>
                        {loading ? <><span className="spinner" /> Analyzing...</> : <><HiOutlinePlay /> Run Pipeline</>}
                    </button>
                </div>
                <div className="form-hints">
                    <span><HiOutlineShieldCheck /> OWASP-compliant input validation</span>
                    <span>11-stage LangGraph pipeline</span>
                    <span>NVIDIA LLaMA 3.3 70B</span>
                </div>
            </form>

            {loading && (
                <div className="card loading-card fade-in">
                    <div className="loading-content">
                        <div className="spinner spinner-lg" />
                        <div>
                            <h3>Pipeline Running for "{company}"</h3>
                            <p>Searching → Scraping → Validating → Extracting → Verifying → Scoring → Synthesizing</p>
                            <div className="loading-bar"><div className="loading-bar-fill" /></div>
                        </div>
                    </div>
                </div>
            )}

            {error && (
                <div className="card error-card fade-in">
                    <HiOutlineExclamationCircle className="error-icon" />
                    <div>
                        <h3>Pipeline Error</h3>
                        <p>{error}</p>
                    </div>
                </div>
            )}

            {result && report && (
                <div className="result-section fade-in-up">
                    <div className="card result-header">
                        <div className="result-meta">
                            <h2>Intelligence Report: {report.company_name || company}</h2>
                            <div className="result-badges">
                                <span className="badge badge-success">{report.total_features_verified || report.features?.length || 0} Features</span>
                                <span className="badge badge-info">{report.total_sources_analysed || 0} Sources</span>
                                {report.generated_at && (
                                    <span className="badge badge-warning">{new Date(report.generated_at).toLocaleString()}</span>
                                )}
                            </div>
                        </div>
                    </div>

                    {report.executive_summary && (
                        <div className="card executive-summary">
                            <h3>📋 Executive Summary</h3>
                            <p>{report.executive_summary}</p>
                        </div>
                    )}

                    {report.features && report.features.length > 0 && (
                        <div className="features-list">
                            <h3 className="section-title">🔬 Discovered Features</h3>
                            {report.features.map((f, i) => (
                                <div key={i} className="card feature-card fade-in-up">
                                    <div className="feature-header">
                                        <div className="feature-rank">#{f.rank || i + 1}</div>
                                        <div className="feature-title-area">
                                            <h4>{f.title || f.feature_title || 'Untitled Feature'}</h4>
                                            {f.category && <span className="badge badge-info">{f.category}</span>}
                                        </div>
                                        {f.confidence_score != null && (
                                            <div className={`confidence-badge ${f.confidence_score >= 0.7 ? 'high' : f.confidence_score >= 0.4 ? 'mid' : 'low'}`}>
                                                {(f.confidence_score * 100).toFixed(0)}%
                                            </div>
                                        )}
                                    </div>
                                    <p className="feature-description">{f.description || f.feature_summary || ''}</p>
                                    <div className="feature-footer">
                                        {f.source_count && <span className="feature-meta">📊 {f.source_count} source{f.source_count > 1 ? 's' : ''}</span>}
                                        {f.key_metrics && f.key_metrics.length > 0 && (
                                            <div className="feature-metrics">
                                                {f.key_metrics.map((m, j) => <span key={j} className="metric-tag">{m}</span>)}
                                            </div>
                                        )}
                                        {f.source_url && (
                                            <a href={f.source_url} target="_blank" rel="noopener noreferrer" className="source-link">
                                                <HiOutlineExternalLink /> Source
                                            </a>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {report.all_sources && report.all_sources.length > 0 && (
                        <div className="card sources-section">
                            <h3>🔗 All Sources ({report.all_sources.length})</h3>
                            <div className="sources-list">
                                {report.all_sources.map((url, i) => (
                                    <a key={i} href={url} target="_blank" rel="noopener noreferrer" className="source-item">
                                        <HiOutlineExternalLink /> {url.length > 80 ? url.slice(0, 80) + '...' : url}
                                    </a>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
