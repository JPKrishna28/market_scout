import { NavLink, useLocation } from 'react-router-dom';
import { HiOutlineHome, HiOutlinePlay, HiOutlineDocumentText, HiOutlineUserGroup, HiOutlineChartBar, HiOutlineX } from 'react-icons/hi';
import { SiPrometheus, SiGrafana } from 'react-icons/si';
import './Sidebar.css';

const NAV_ITEMS = [
    { path: '/', label: 'Dashboard', icon: <HiOutlineHome /> },
    { path: '/run', label: 'Run Pipeline', icon: <HiOutlinePlay /> },
    { path: '/reports', label: 'Reports', icon: <HiOutlineDocumentText /> },
    { path: '/competitors', label: 'Competitors', icon: <HiOutlineUserGroup /> },
];

const EXTERNAL_LINKS = [
    { href: 'https://api.market-scout.me/docs', label: 'API Docs', icon: <HiOutlineChartBar /> },
    { href: 'https://metrics.market-scout.me', label: 'Prometheus', icon: <SiPrometheus /> },
    { href: 'https://grafana.market-scout.me', label: 'Grafana', icon: <SiGrafana /> },
];

export default function Sidebar({ isOpen, onClose }) {
    const location = useLocation();

    return (
        <aside className={`sidebar ${isOpen ? 'sidebar-mobile-open' : ''}`}>
            <div className="sidebar-header">
                <div className="sidebar-brand">
                    <div className="brand-icon">🔍</div>
                    <div>
                        <h1>Market Scout</h1>
                        <span className="brand-subtitle">Intelligence Platform</span>
                    </div>
                </div>
                <button 
                    className="sidebar-close-btn"
                    onClick={onClose}
                    aria-label="Close menu"
                >
                    <HiOutlineX />
                </button>
            </div>

            <nav className="sidebar-nav">
                <div className="nav-section">
                    <span className="nav-section-label">Navigation</span>
                    {NAV_ITEMS.map(item => (
                        <NavLink
                            key={item.path}
                            to={item.path}
                            onClick={onClose}
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
                        <a key={link.href} href={link.href} target="_blank" rel="noopener noreferrer" className="nav-item external" onClick={onClose}>
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
