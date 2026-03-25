import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getCompetitors, getHealth } from "../api";
import {
  HiOutlinePlay,
  HiOutlineDocumentText,
  HiOutlineUserGroup,
  HiOutlineShieldCheck,
  HiOutlineClock,
  HiOutlineSparkles,
} from "react-icons/hi";
import ThemeToggle from "./ThemeToggle";
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
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-secondary)] font-sans p-8">
      {/* Header */}

      <div className="page-header flex justify-between items-start">

        <div>
            <h1 className="text-[var(--text-primary)] text-3xl font-bold mb-1">
                Welcome to Market Scout
           </h1>

            <p className="text-[var(--text-secondary)]">
                    Your AI-powered competitive intelligence platform
            </p>
        </div>

            <ThemeToggle />

      </div>

      {/* Stats Grid */}

      <div className="stats-grid stagger">
        <StatCard
          icon={<HiOutlineUserGroup />}
          value={loading ? "—" : competitors.length}
          label="Tracked Companies"
          bg="var(--info-bg)"
          color="var(--info)"
        />

        <StatCard
          icon={<HiOutlineShieldCheck />}
          value={health ? "Online" : "—"}
          label="System Status"
          bg="var(--success-bg)"
          color="var(--success)"
        />

        <StatCard
          icon={<HiOutlineSparkles />}
          value="LLaMA 3.3"
          label="LLM Engine"
          bg="rgba(139,92,246,0.12)"
          color="#a78bfa"
        />

        <StatCard
          icon={<HiOutlineClock />}
          value="7 Days"
          label="Recency Window"
          bg="var(--warning-bg)"
          color="var(--warning)"
        />
      </div>

      {/* Dashboard Grid */}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 mb-8">
        <ActionCard
          icon={<HiOutlinePlay />}
          title="Run Intelligence Pipeline"
          desc="Enter a company name and generate a comprehensive technical feature report in seconds."
          bg="rgba(99,102,241,0.15)"
          color="var(--accent-secondary)"
          onClick={() => navigate("/run")}
        />

        <ActionCard
          icon={<HiOutlineDocumentText />}
          title="View Historical Reports"
          desc="Browse past intelligence reports with executive summaries, confidence scores, and citations."
          bg="rgba(34,197,94,0.12)"
          color="#22c55e"
          onClick={() => navigate("/reports")}
        />

        <ActionCard
          icon={<HiOutlineUserGroup />}
          title="Manage Competitors"
          desc="View and track the companies in your competitive landscape."
          bg="rgba(245,158,11,0.12)"
          color="#f59e0b"
          onClick={() => navigate("/competitors")}
        />
      </div>

      {/* Pipeline Section */}
      <div className="card fade-in-up">

          <h3 className="text-[1.15rem] font-semibold mb-7 flex items-center gap-2">
              🔗 Pipeline Architecture
          </h3>

          <div className="flex flex-wrap gap-5">

              {pipelineSteps.map((item, i) => (

              <div
                  key={i}
                  className="flex items-center gap-3 px-5 py-3
                  bg-[rgba(99,102,241,0.06)]
                  border border-[rgba(99,102,241,0.12)]
                  rounded-[var(--radius-md)]
                  transition-all
                  hover:bg-[rgba(99,102,241,0.12)]
                  hover:border-[var(--border-accent)]"
              >

                  <div
                  className="w-8 h-8 flex items-center justify-center
                  rounded-full text-white text-[0.85rem] font-bold"
                  style={{ background: "var(--gradient-brand)" }}
                  >
                  {item.step}
              </div>

              <div className="flex flex-col leading-tight">

                  <strong className="text-[0.9rem] font-semibold text-[var(--text-primary)]">
                  {item.label}
                  </strong>

                  <span className="text-[0.78rem] text-[var(--text-muted)]">
                  {item.desc}
                  </span>

              </div>

          </div>

              ))}

      </div>

</div>
    </div>
  );
}

function StatCard({ icon, value, label, bg, color }) {
  return (
    <div className="stat-card fade-in-up">
      <div className="stat-icon" style={{ background: bg, color: color }}>
        {icon}
      </div>

      <div className="stat-info">
        <h3 className="text-[0.98rem] font-bold text-[var(--text-primary)]">{value}</h3>
        <p>{label}</p>
      </div>
    </div>
  );
}

function ActionCard({ icon, title, desc, bg, color, onClick }) {
  return (
    <div
      className="card quick-action fade-in-up flex items-center gap-5 cursor-pointer min-h-[110px]"
      onClick={onClick}
    >
      <div
        className="flex items-center justify-center
w-14 h-14 rounded-[var(--radius-md)]
text-[1.6rem]"
        style={{ background: bg, color: color }}
      >
        {icon}
      </div>

      <div className="quick-action-content">
      <h3 className="text-[0.98rem] font-bold text-[var(--text-primary)]">
{title}
</h3>
<p className="text-[0.85rem] text-[var(--text-secondary)] leading-relaxed">
{desc}
</p>
      </div>

      <span className="quick-action-arrow">→</span>
    </div>
  );
}

const pipelineSteps = [
  { step: "1", label: "Guardrails", desc: "OWASP security checks" },
  { step: "2", label: "Search Planning", desc: "LLM query generation" },
  { step: "3", label: "Web Search", desc: "Tavily API execution" },
  { step: "4", label: "Smart Scraping", desc: "3-tier fallback cascade" },
  { step: "5", label: "Date Validation", desc: "7-day recency filter" },
  { step: "6", label: "Content Filter", desc: "Technical relevance check" },
  { step: "7", label: "Authority Check", desc: "Source credibility scoring" },
  {
    step: "8",
    label: "Feature Extraction",
    desc: "Structured data extraction",
  },
  { step: "9", label: "Verification", desc: "SBERT cross-source clustering" },
  { step: "10", label: "Scoring", desc: "Multi-signal confidence" },
  { step: "11", label: "Synthesis", desc: "Executive report generation" },
];
