import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { HiOutlineUserGroup, HiOutlinePlay, HiOutlineCalendar } from 'react-icons/hi';
import { getCompetitors } from '../api';
import './Competitors.css';

export default function Competitors() {
    const [competitors, setCompetitors] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        async function load() {
            try {
                const data = await getCompetitors();
                setCompetitors(data);
            } catch {
                setCompetitors([]);
            } finally {
                setLoading(false);
            }
        }
        load();
    }, []);

    return (
        <div className="competitors-page fade-in">
            <div className="page-header">
                <h1>Tracked Competitors</h1>
                <p>Companies that have been analyzed through the intelligence pipeline</p>
            </div>

            {loading && (
                <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
                    <div className="spinner spinner-lg" style={{ margin: '0 auto 12px' }} />
                    <p style={{ color: 'var(--text-secondary)' }}>Loading competitors...</p>
                </div>
            )}

            {!loading && competitors.length === 0 && (
                <div className="empty-state">
                    <div className="icon"><HiOutlineUserGroup /></div>
                    <h3>No competitors tracked yet</h3>
                    <p>Run the intelligence pipeline on a company to start tracking them.</p>
                    <button className="btn btn-primary" style={{ marginTop: '16px' }} onClick={() => navigate('/run')}>
                        <HiOutlinePlay /> Run Pipeline
                    </button>
                </div>
            )}

            {!loading && competitors.length > 0 && (
                <div className="competitors-grid stagger">
                    {competitors.map((comp, i) => (
                        <div key={comp.id || i} className="card competitor-card fade-in-up">
                            <div className="competitor-avatar">
                                {(comp.name || '?')[0].toUpperCase()}
                            </div>
                            <div className="competitor-info">
                                <h3>{comp.name}</h3>
                                {comp.industry && <span className="badge badge-info">{comp.industry}</span>}
                                {comp.created_at && (
                                    <p className="competitor-date">
                                        <HiOutlineCalendar /> Added {new Date(comp.created_at).toLocaleDateString()}
                                    </p>
                                )}
                            </div>
                            <button className="btn btn-secondary" onClick={() => { navigate('/run'); }}>
                                <HiOutlinePlay /> Analyze
                            </button>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
