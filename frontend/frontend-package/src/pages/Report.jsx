// src/pages/Report.jsx
import { useEffect, useState } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { Download, ArrowLeft, AlertTriangle, ShieldX, CheckCircle } from 'lucide-react'
import { getAnalysis, getReportUrl } from '../hooks/useApi'
import ScoreRing from '../components/ScoreRing'

export default function Report() {
  const { id }       = useParams()
  const location     = useLocation()
  const navigate     = useNavigate()
  const [data, setData]   = useState(location.state || null)
  const [tab, setTab]     = useState('overview')
  const [loading, setLoading] = useState(!location.state)

  useEffect(() => {
    if (!data) {
      getAnalysis(id).then(setData).finally(() => setLoading(false))
    }
  }, [id])

  if (loading) return (
    <div className="main-content">
      <div className="loading-overlay"><div className="spinner" /></div>
    </div>
  )

  if (!data) return (
    <div className="main-content">
      <div className="page-body">
        <div className="empty-state">Analysis not found.</div>
      </div>
    </div>
  )

  const highCount   = data.found_clauses?.filter(c => c.risk_level === 'high').length   || 0
  const medCount    = data.found_clauses?.filter(c => c.risk_level === 'medium').length || 0
  const missCount   = data.missing_clauses?.length || 0
  const critCount   = data.critical_missing?.length || 0

  return (
    <div className="main-content">
      <div className="page-header">
        <div className="flex items-center justify-between">
          <div>
            <button
              className="btn btn-ghost"
              style={{ padding: '4px 10px', marginBottom: 8, fontSize: '0.8rem' }}
              onClick={() => navigate('/')}
            >
              <ArrowLeft size={14} /> Back
            </button>
            <h1>{data.filename}</h1>
            <p>{data.contract_type} · {data.word_count?.toLocaleString()} words · {data.page_count} page{data.page_count !== 1 ? 's' : ''}</p>
          </div>
          <a
            href={getReportUrl(data.analysis_id)}
            download
            className="btn btn-primary"
          >
            <Download size={15} />
            Download PDF Report
          </a>
        </div>
      </div>

      <div className="page-body">
        {/* Summary strip */}
        <div className="card mb-4" style={{ background: 'var(--bg-elevated)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
            <ScoreRing score={data.overall_score} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '0.83rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
                {data.risk_summary}
              </div>
              <div style={{ display: 'flex', gap: 20 }}>
                <Stat val={highCount}  label="High-risk clauses" color="var(--red)" />
                <Stat val={medCount}   label="Medium-risk clauses" color="var(--orange)" />
                <Stat val={missCount}  label="Missing protections" color="var(--yellow)" />
                <Stat val={critCount}  label="Critical gaps" color="var(--red)" />
              </div>
            </div>
          </div>
        </div>

        {/* Per-party dashboard */}
        <div className="party-grid mb-4">
          <PartyCard party={data.party_a} />
          <PartyCard party={data.party_b} />
        </div>

        {/* Tabs */}
        <div className="tabs">
          {[
            ['overview',  `Red Flags (${data.red_flags?.length || 0})`],
            ['clauses',   `Risk Clauses (${data.found_clauses?.length || 0})`],
            ['missing',   `Missing Clauses (${missCount})`],
          ].map(([key, label]) => (
            <button
              key={key}
              className={`tab ${tab === key ? 'active' : ''}`}
              onClick={() => setTab(key)}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {tab === 'overview' && <OverviewTab flags={data.red_flags} />}
        {tab === 'clauses'  && <ClausesTab  clauses={data.found_clauses} />}
        {tab === 'missing'  && <MissingTab  missing={data.missing_clauses} />}
      </div>
    </div>
  )
}

function Stat({ val, label, color }) {
  return (
    <div>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '1.5rem', fontWeight: 500, color }}>
        {val}
      </div>
      <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </div>
    </div>
  )
}

function PartyCard({ party }) {
  if (!party) return null
  const cls = party.risk_score >= 70 ? 'high' : party.risk_score >= 40 ? 'medium' : 'low'
  return (
    <div className="party-card">
      <div className="party-name">{party.name}</div>
      <ScoreRing score={party.risk_score} />
      <div className="party-stats">
        <div style={{ textAlign: 'center' }}>
          <div className="party-stat-val" style={{ color: 'var(--red)' }}>{party.high_risk_count}</div>
          <div className="party-stat-label">High risk</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div className="party-stat-val" style={{ color: 'var(--orange)' }}>{party.med_risk_count}</div>
          <div className="party-stat-label">Medium</div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div className="party-stat-val" style={{ color: 'var(--green)' }}>{party.low_risk_count}</div>
          <div className="party-stat-label">Low risk</div>
        </div>
      </div>
    </div>
  )
}

function OverviewTab({ flags }) {
  if (!flags?.length) return (
    <div className="empty-state">
      <CheckCircle size={32} color="var(--green)" style={{ margin: '0 auto 12px' }} />
      No red flags detected — this contract appears relatively balanced.
    </div>
  )
  return (
    <div>
      {flags.map((f, i) => (
        <div key={i} className="red-flag-item">
          <AlertTriangle size={15} color="var(--red)" style={{ flexShrink: 0, marginTop: 1 }} />
          {f}
        </div>
      ))}
    </div>
  )
}

function ClausesTab({ clauses }) {
  if (!clauses?.length) return (
    <div className="empty-state">No risk clauses identified in this contract.</div>
  )

  const sorted = [...clauses].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 }
    return (order[a.risk_level] ?? 2) - (order[b.risk_level] ?? 2)
  })

  return (
    <div>
      {sorted.map((c, i) => (
        <div key={i} className={`clause-card risk-${c.risk_level}`}>
          <div className="clause-header">
            <span className="clause-name">{c.category}</span>
            <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
              <span className={`badge badge-${c.risk_level}`}>{c.risk_level}</span>
              {c.party_burdened && (
                <span className="badge" style={{ background: 'var(--bg-base)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
                  {c.party_burdened}
                </span>
              )}
            </div>
          </div>
          {c.plain_language && (
            <div className="clause-body">{c.plain_language}</div>
          )}
          {c.excerpt && (
            <div className="clause-excerpt">"{c.excerpt}"</div>
          )}
          {c.recommendation && (
            <div className="clause-rec">
              <span style={{ flexShrink: 0 }}>→</span>
              {c.recommendation}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function MissingTab({ missing }) {
  if (!missing?.length) return (
    <div className="empty-state">
      <CheckCircle size={32} color="var(--green)" style={{ margin: '0 auto 12px' }} />
      All standard protective clauses are present in this contract.
    </div>
  )

  const sorted = [...missing].sort((a, b) => {
    const order = { critical: 0, high: 1, medium: 2 }
    return (order[a.severity] ?? 2) - (order[b.severity] ?? 2)
  })

  return (
    <div className="card">
      {sorted.map((m, i) => (
        <div key={i} className="missing-row">
          <div style={{ flexShrink: 0, marginTop: 2 }}>
            <ShieldX size={16} color={m.severity === 'critical' ? 'var(--red)' : 'var(--orange)'} />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span className="missing-name">{m.clause}</span>
              <span className={`badge badge-${m.severity === 'critical' ? 'critical' : 'missing'}`}>
                {m.severity}
              </span>
            </div>
            <div className="missing-reason">{m.reason}</div>
            {m.indian_context && (
              <div className="missing-india">🇮🇳 {m.indian_context}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
