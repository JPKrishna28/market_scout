import { useState } from 'react';
import { HiOutlinePlay, HiOutlineSparkles, HiOutlineExternalLink, HiOutlineShieldCheck, HiOutlineExclamationCircle } from 'react-icons/hi';
import { runPipeline } from '../api';

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

            <form className="run-form card p-6" onSubmit={handleRun}>

  <div className="flex items-center gap-4">

    <div className="relative flex-1">

      

      <input
        type="text"
        className="input pipeline-input pl-20 h-[52px] text-[0.95rem] w-full"
        placeholder="Enter company name (e.g. OpenAI, Google DeepMind, Anthropic)"
        value={company}
        onChange={e => setCompany(e.target.value)}
        disabled={loading}
        maxLength={200}
      />

    </div>

    <button
      type="submit"
      className="btn btn-primary run-btn h-[52px] px-6 whitespace-nowrap"
      disabled={loading || !company.trim()}
    >
      {loading ? (
        <>
          <span className="spinner" /> Analyzing...
        </>
      ) : (
        <>
          <HiOutlinePlay /> Run Pipeline
        </>
      )}
    </button>

  </div>

  <div className="flex gap-6 text-[0.8rem] text-[var(--text-muted)] mt-3">

    <span className="flex items-center gap-1">
      <HiOutlineShieldCheck />
      OWASP-compliant input validation
    </span>

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
                <div className="result-section fade-in-up mt-6">
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
  <div className="card fade-in-up mt-6 p-6">

    {/* Header */}
    <h3 className="flex items-center gap-2 text-[1.1rem] font-semibold text-[var(--text-primary)] mb-3">
      Executive Summary
    </h3>

    {/* Content */}
    <p className="
      text-[0.92rem]
      leading-relaxed
      text-[var(--text-secondary)]
      max-w-[900px]
    ">
      {report.executive_summary}
    </p>

  </div>
)}
{report.features && report.features.length > 0 && (
  <div className="features-list">
    <h3 className="text-[1.15rem] font-semibold mb-6 flex items-center gap-2 mt-6">
      🔬 Discovered Features
    </h3>

    {report.features.map((f, i) => (
      <div
        key={i}
        className="card fade-in-up mt-6 p-5"
      >

        {/* HEADER */}
        <div className="flex items-start justify-between gap-3">

{/* Left side: index + title */}
<div className="flex items-start gap-3">

  {/* Rank */}
  <div className="text-[0.9rem] font-bold text-[var(--text-muted)] mt-[2px]">
    {f.rank || i + 1}
  </div>

  {/* Title + Category */}
  <div className="flex flex-col gap-1">

    <div className="flex items-center flex-wrap gap-2">

      <h4 className="text-[0.98rem] font-semibold text-[var(--text-primary)]">
        {f.title || f.feature_title || "Untitled Feature"}
      </h4>

      {f.category && (
        <span className="badge badge-info">
          {f.category}
        </span>
      )}

    </div>

  </div>

</div>

{/* Confidence */}
{f.confidence_score != null && (
  <div
    className={`text-[0.75rem] font-semibold px-2 py-[4px] rounded-full whitespace-nowrap
    ${
      f.confidence_score >= 0.7
        ? "bg-green-500/15 text-green-500"
        : f.confidence_score >= 0.4
        ? "bg-yellow-500/15 text-yellow-500"
        : "bg-red-500/15 text-red-500"
    }`}
  >
    {(f.confidence_score * 100).toFixed(0)}%
  </div>
)}

</div>

        {/* DESCRIPTION */}
        <p className="text-[0.9rem] leading-relaxed text-[var(--text-secondary)] mt-3">
          {f.description || f.feature_summary || ""}
        </p>

        {/* FOOTER */}
        <div className="flex flex-wrap items-center gap-4 mt-4 text-[0.82rem]">

          {f.source_count && (
            <span className="text-[var(--text-muted)]">
              📊 {f.source_count} source{f.source_count > 1 ? "s" : ""}
            </span>
          )}

          {f.key_metrics && f.key_metrics.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {f.key_metrics.map((m, j) => (
                <span
                  key={j}
                  className="px-2 py-[2px] rounded bg-green-500/10 text-green-500 text-[0.72rem] font-medium"
                >
                  {m}
                </span>
              ))}
            </div>
          )}

          {f.source_url && (
            <a
              href={f.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-green-500 hover:text-green-600 font-medium"
            >
              <HiOutlineExternalLink />
              Source
            </a>
          )}
        </div>
      </div>
    ))}
  </div>
)}

{report.all_sources && report.all_sources.length > 0 && (
  <div className="card fade-in-up mt-6 p-5">

    {/* Header */}
    <h3 className="text-[1.1rem] font-semibold mb-4 flex items-center gap-2">
      🔗 All Sources
      <span className="text-[0.8rem] font-medium text-[var(--text-muted)]">
        ({report.all_sources.length})
      </span>
    </h3>

    {/* Sources Grid */}
    <div className="grid gap-3">

      {report.all_sources.map((url, i) => (
        <a
          key={i}
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="
            flex items-center gap-3
            px-4 py-3
            rounded-[var(--radius-md)]
            border border-[var(--border-subtle)]
            bg-[rgba(0,0,0,0.02)]
            hover:bg-[rgba(0,0,0,0.05)]
            transition
            group
          "
        >

          {/* Icon */}
          <HiOutlineExternalLink className="text-[1rem] text-green-500 flex-shrink-0 group-hover:scale-105 transition" />

          {/* URL */}
          <span className="text-[0.85rem] text-[var(--text-secondary)] break-all">
            {url.length > 90 ? url.slice(0, 90) + "..." : url}
          </span>

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
