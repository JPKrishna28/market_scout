import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import Dashboard from './pages/Dashboard';
import RunPipeline from './pages/RunPipeline';
import Reports from './pages/Reports';
import Competitors from './pages/Competitors';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <Header />
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
