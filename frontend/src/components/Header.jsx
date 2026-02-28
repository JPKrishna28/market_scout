import { useLocation } from 'react-router-dom';
import './Header.css';

const PAGE_TITLES = {
    '/': 'Dashboard',
    '/run': 'Run Pipeline',
    '/reports': 'Reports',
    '/competitors': 'Competitors',
};

export default function Header() {
    const location = useLocation();
    const title = PAGE_TITLES[location.pathname] || 'Market Scout';

    return (
        <header className="header">
            <div className="header-left">
                <h2 className="header-title">{title}</h2>
            </div>
            <div className="header-right">
                <div className="header-status">
                    <span className="status-dot" />
                    <span className="status-text">Backend Connected</span>
                </div>
            </div>
        </header>
    );
}
