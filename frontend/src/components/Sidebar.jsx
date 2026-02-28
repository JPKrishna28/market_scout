import { NavLink, useLocation } from 'react-router-dom';
import { HiOutlineHome, HiOutlinePlay, HiOutlineDocumentText, HiOutlineUserGroup, HiOutlineChartBar } from 'react-icons/hi';
import { SiPrometheus, SiGrafana } from 'react-icons/si';
import './Sidebar.css';

const NAV_ITEMS = [
    { path: '/', label: 'Dashboard', icon: <HiOutlineHome /> },
    { path: '/run', label: 'Run Pipeline', icon: <HiOutlinePlay /> },
    { path: '/reports', label: 'Reports', icon: <HiOutlineDocumentText /> },
    { path: '/competitors', label: 'Competitors', icon: <HiOutlineUserGroup /> },
];

const EXTERNAL_LINKS = [
    { href: 'http://localhost:8000/docs', label: 'API Docs', icon: <HiOutlineChartBar /> },
    { href: 'http://localhost:9090', label: 'Prometheus', icon: <SiPrometheus /> },
    { href: 'http://localhost:3000', label: 'Grafana', icon: <SiGrafana /> },
];

export default function Sidebar() {
    const location = useLocation();

    return (
        <aside className="sidebar">
            <div className="sidebar-brand">
                <div className="brand-icon">🔍</div>
                <div>
                    <h1>Market Scout</h1>
                    <span className="brand-subtitle">Intelligence Platform</span>
                </div>
            </div>

            <nav className="sidebar-nav">
                <div className="nav-section">
                    <span className="nav-section-label">Navigation</span>
                    {NAV_ITEMS.map(item => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                            end={item.path === '/'}
                        >
                            <span className="nav-icon">{item.icon}</span>
                            <span className="nav-label">{item.label}</span>
                            {item.path === location.pathname && <span className="nav-indicator" />}
                        </NavLink>
                    ))}
                </div>

                <div className="nav-section">
                    <span className="nav-section-label">External</span>
                    {EXTERNAL_LINKS.map(link => (
                        <a key={link.href} href={link.href} target="_blank" rel="noopener noreferrer" className="nav-item external">
                            <span className="nav-icon">{link.icon}</span>
                            <span className="nav-label">{link.label}</span>
                            <span className="nav-external-badge">↗</span>
                        </a>
                    ))}
                </div>
            </nav>

            <div className="sidebar-footer">
                <div className="footer-badge">v2.0</div>
                <span>Pipeline Engine</span>
            </div>
        </aside>
    );
}
