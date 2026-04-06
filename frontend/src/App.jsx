import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { useState } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import RunPipeline from './pages/RunPipeline';
import Reports from './pages/Reports';
import Competitors from './pages/Competitors';
export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        {/* Mobile menu overlay */}
        {sidebarOpen && (
          <div 
            className="sidebar-overlay" 
            onClick={() => setSidebarOpen(false)}
          />
        )}
        {/* Mobile menu toggle button */}
        <button
          className="mobile-menu-btn"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          aria-label="Toggle menu"
        >
          <span></span>
          <span></span>
          <span></span>
        </button>
        {/* <Header /> */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/run" element={<RunPipeline />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/competitors" element={<Competitors />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
