import { useState } from 'react';
import { HiOutlineSearch, HiOutlineDocumentText, HiOutlineExternalLink } from 'react-icons/hi';
import { getReports } from '../api';
import './Reports.css';

export default function Reports() {
    const [company, setCompany] = useState('');
    const [reports, setReports] = useState([]);
    const [loading, setLoading] = useState(false);
    const [searched, setSearched] = useState(false);
    const [expanded, setExpanded] = useState(null);

    const handleSearch = async (e) => {
        e.preventDefault();
        if (!company.trim()) return;
        setLoading(true);
        setSearched(true);
        try {
            const data = await getReports(company.trim());
            setReports(Array.isArray(data) ? data : [data]);
        } catch {
            setReports([]);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="reports-page fade-in">
            <div className="page-header">
                <h1>Intelligence Reports</h1>
                <p>Search and browse historical intelligence reports by company name</p>
            </div>

            <form className="card search-form" onSubmit={handleSearch}>
                <div className="form-row">
                    <div className="input-wrapper">
                        <HiOutlineSearch className="input-icon" />
                        <input
                            className="input pipeline-input"
                            placeholder="Search reports by company name..."
                            value={company}
                            onChange={e => setCompany(e.target.value)}
                        />
                    </div>
                    <button type="submit" className="btn btn-primary" disabled={loading || !company.trim()}>
                        {loading ? <span className="spinner" /> : <><HiOutlineSearch /> Search</>}
                    </button>
                </div>
            </form>

            {loading && (
                <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
                    <div className="spinner spinner-lg" style={{ margin: '0 auto 12px' }} />
                    <p style={{ color: 'var(--text-secondary)' }}>Loading reports...</p>
                </div>
            )}

            {searched && !loading && reports.length === 0 && (
                <div className="empty-state">
                    <div className="icon"><HiOutlineDocumentText /></div>
                    <h3>No reports found</h3>
                    <p>No intelligence reports found for "{company}". Try running the pipeline first.</p>
                </div>
            )}

            {!loading && reports.length > 0 && (
                <div className="reports-list stagger">
                    {reports.map((report, i) => (
                        <div
                            key={report.id || i}
                            className={`card report-card fade-in-up ${expanded === i ? 'expanded' : ''}`}
                            onClick={() => setExpanded(expanded === i ? null : i)}
                        >
                            <div className="report-card-header">
                                <div className="report-icon"><HiOutlineDocumentText /></div>
                                <div className="report-info">
                                    <h3>{report.company_name || company}</h3>
                                    <div className="report-meta">
                                        {report.created_at && <span>{new Date(report.created_at).toLocaleDateString()}</span>}
                                        <span>{report.total_features || 0} features</span>
                                        <span>{report.total_sources || 0} sources</span>
                                    </div>
                                </div>
                                <span className="expand-arrow">{expanded === i ? '▲' : '▼'}</span>
                            </div>

                            {expanded === i && (
                                <div className="report-details fade-in">
                                    {report.executive_summary && (
                                        <div className="report-summary">
                                            <h4>Executive Summary</h4>
                                            <p>{report.executive_summary}</p>
                                        </div>
                                    )}
                                    {report.all_sources && report.all_sources.length > 0 && (
                                        <div className="report-sources">
                                            <h4>Sources</h4>
                                            {report.all_sources.map((url, j) => (
                                                <a key={j} href={url} target="_blank" rel="noopener noreferrer" className="source-item">
                                                    <HiOutlineExternalLink /> {url.length > 70 ? url.slice(0, 70) + '...' : url}
                                                </a>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
