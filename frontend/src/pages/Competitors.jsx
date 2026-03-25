import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { HiOutlineUserGroup, HiOutlinePlay, HiOutlineCalendar } from 'react-icons/hi';
import { getCompetitors } from '../api';

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
                <div className="card flex flex-col items-center justify-center py-10">
                <div className="spinner spinner-lg mb-3" />
                <p className="text-[var(--text-secondary)]">Loading competitors...</p>
            </div>
            )}

            {!loading && competitors.length === 0 && (
              <div className="empty-state flex flex-col items-center justify-center text-center mt-20">
                    <div className="icon"><HiOutlineUserGroup /></div>
                    <h3>No competitors tracked yet</h3>
                    <p>Run the intelligence pipeline on a company to start tracking them.</p>
                    <button className="btn btn-primary mt-4" onClick={() => navigate('/run')}>
                        <HiOutlinePlay /> Run Pipeline
                    </button>
                </div>
            )}

            {!loading && competitors.length > 0 && (
                <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-5 stagger">
                    {competitors.map((comp, i) => (
                        <div key={comp.id || i} className="card fade-in-up flex items-center justify-between gap-4">
                            <div className="w-12 h-12 flex items-center justify-center rounded-[var(--radius-md)] 
bg-[rgba(99,102,241,0.15)] text-[var(--accent-secondary)] font-bold text-lg">
                                {(comp.name || '?')[0].toUpperCase()}
                            </div>
                            <div className="flex flex-col flex-1">
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
