import { useState } from "react";
import {
  HiOutlineSearch,
  HiOutlineDocumentText,
  HiOutlineExternalLink,
  HiChevronDown,
  HiChevronUp
} from "react-icons/hi";
import { getReports } from "../api";

export default function Reports() {

  const [company, setCompany] = useState("");
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

      {/* Page Header */}

      <div className="page-header">
        <h1>Intelligence Reports</h1>
        <p>
          Search and browse historical intelligence reports by company name
        </p>
      </div>

      {/* Search Form */}

      <form className="card p-6" onSubmit={handleSearch}>

        <div className="flex items-center gap-4">

          <div className="relative flex-1">

            <HiOutlineSearch
              className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--accent-secondary)] text-lg"
            />

            <input
              className="input pl-16 pr-4 py-3 h-[52px] w-full"
              placeholder="Search reports by company name..."
              value={company}
              onChange={(e) => setCompany(e.target.value)}
            />

          </div>

          <button
            type="submit"
            className="btn btn-primary h-[52px] px-6 whitespace-nowrap"
            disabled={loading || !company.trim()}
          >

            {loading ? (
              <span className="spinner" />
            ) : (
              <>
                <HiOutlineSearch />
                Search
              </>
            )}

          </button>

        </div>

      </form>

      {/* Loading State */}

      {loading && (
        <div className="card text-center py-10 mt-4">
          <div className="spinner spinner-lg mx-auto mb-3" />
          <p className="text-[var(--text-secondary)]">
            Loading reports...
          </p>
        </div>
      )}

      {/* Empty State */}

      {searched && !loading && reports.length === 0 && (
        <div className="empty-state">

          <div className="icon">
            <HiOutlineDocumentText />
          </div>

          <h3>No reports found</h3>

          <p>
            No intelligence reports found for "{company}".
            Try running the pipeline first.
          </p>

        </div>
      )}

      {/* Reports List */}

      {!loading && reports.length > 0 && (

        <div className="reports-list mt-6 space-y-4">

          {reports.map((report, i) => (

            <div
              key={report.id || i}
              className={`card p-5 cursor-pointer transition hover:-translate-y-[2px] ${
                expanded === i ? "border-[var(--accent-primary)]" : ""
              }`}
              onClick={() =>
                setExpanded(expanded === i ? null : i)
              }
            >

              {/* Report Header */}

              <div className="flex items-start justify-between">

                <div className="flex items-start gap-3">

                  <div className="text-[1.1rem] text-[var(--accent-secondary)]">
                    <HiOutlineDocumentText />
                  </div>

                  <div className="flex flex-col gap-1">

                    <h3 className="text-[0.98rem] font-semibold text-[var(--text-primary)]">
                      {report.company_name || company}
                    </h3>

                    <div className="flex items-center flex-wrap gap-2 text-[0.8rem] text-[var(--text-muted)]">

                      {report.created_at && (
                        <span>
                          {new Date(
                            report.created_at
                          ).toLocaleDateString()}
                        </span>
                      )}

                      <span>•</span>

                      <span>
                        {report.total_features || 0} features
                      </span>

                      <span>•</span>

                      <span>
                        {report.total_sources || 0} sources
                      </span>

                    </div>

                  </div>

                </div>

                <div className="text-[var(--text-muted)] text-lg">

                  {expanded === i ? (
                    <HiChevronUp />
                  ) : (
                    <HiChevronDown />
                  )}

                </div>

              </div>

              {/* Expanded Details */}

              {expanded === i && (

                <div className="mt-4 pt-4 border-t border-[var(--border-subtle)] fade-in">

                  {/* Executive Summary */}

                  {report.executive_summary && (

                    <div className="mb-4">

                      <h4 className="text-[0.9rem] font-semibold text-[var(--text-primary)] mb-1">
                        Executive Summary
                      </h4>

                      <p className="text-[0.85rem] leading-relaxed text-[var(--text-secondary)]">
                        {report.executive_summary}
                      </p>

                    </div>

                  )}

                  {/* Sources */}

                  {report.all_sources &&
                    report.all_sources.length > 0 && (

                      <div>

                        <h4 className="text-[0.9rem] font-semibold text-[var(--text-primary)] mb-2">
                          Sources
                        </h4>

                        <div className="flex flex-col gap-2">

                          {report.all_sources.map((url, j) => (

                            <a
                              key={j}
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-2 text-[0.8rem] text-green-500 hover:text-green-600"
                            >

                              <HiOutlineExternalLink />

                              {url.length > 70
                                ? url.slice(0, 70) + "..."
                                : url}

                            </a>

                          ))}

                        </div>

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