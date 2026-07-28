// src/pages/History.jsx
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, Download } from 'lucide-react'
import { listAnalyses, getReportUrl } from '../hooks/useApi'

export default function History() {
  const [analyses, setAnalyses] = useState([])
  const [loading, setLoading]   = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    listAnalyses().then(setAnalyses).finally(() => setLoading(false))
  }, [])

  const scoreClass = (s) => s >= 70 ? 'score-high' : s >= 40 ? 'score-medium' : 'score-low'

  return (
    <div className="main-content">
      <div className="page-header">
        <h1>Past Analyses</h1>
        <p>All contracts you've reviewed — click any row to view the full report</p>
      </div>

      <div className="page-body">
        {loading ? (
          <div className="loading-overlay"><div className="spinner" /></div>
        ) : analyses.length === 0 ? (
          <div className="empty-state">
            <FileText size={32} color="var(--text-muted)" style={{ margin: '0 auto 12px' }} />
            No contracts analyzed yet. Upload one to get started.
          </div>
        ) : (
          <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="history-table">
              <thead>
                <tr>
                  <th>Contract</th>
                  <th>Type</th>
                  <th>Risk Score</th>
                  <th>Reviewed Party</th>
                  <th>Date</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {analyses.map((a) => (
                  <tr
                    key={a.id}
                    style={{ cursor: 'pointer' }}
                    onClick={() => navigate(`/report/${a.id}`)}
                  >
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <FileText size={14} color="var(--accent)" />
                        <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                          {a.filename}
                        </span>
                      </div>
                    </td>
                    <td>{a.contract_type || '—'}</td>
                    <td>
                      <span
                        className={`badge ${a.overall_score >= 70 ? 'badge-high' : a.overall_score >= 40 ? 'badge-medium' : 'badge-low'}`}
                      >
                        {a.overall_score}/100
                      </span>
                    </td>
                    <td>{a.party_a_name || '—'}</td>
                    <td>{new Date(a.created_at).toLocaleDateString('en-IN', {
                      day: 'numeric', month: 'short', year: 'numeric'
                    })}</td>
                    <td>
                      <a
                        href={getReportUrl(a.id)}
                        download
                        onClick={(e) => e.stopPropagation()}
                        className="btn btn-ghost"
                        style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                      >
                        <Download size={12} />
                        PDF
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
