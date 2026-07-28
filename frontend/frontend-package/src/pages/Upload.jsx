// src/pages/Upload.jsx
import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload as UploadIcon, FileText, X, AlertCircle } from 'lucide-react'
import { analyzeContract } from '../hooks/useApi'

const STEPS = [
  'Extracting contract text...',
  'Identifying risk clauses (CUAD taxonomy)...',
  'Detecting missing standard protections...',
  'Aggregating per-party risk scores...',
  'Generating risk report...',
]

export default function Upload() {
  const [file, setFile]           = useState(null)
  const [dragging, setDragging]   = useState(false)
  const [partyA, setPartyA]       = useState('')
  const [partyB, setPartyB]       = useState('')
  const [loading, setLoading]     = useState(false)
  const [stepIdx, setStepIdx]     = useState(0)
  const [error, setError]         = useState(null)
  const fileRef                   = useRef()
  const navigate                  = useNavigate()
  const intervalRef               = useRef(null)

  const handleFile = (f) => {
    if (!f) return
    const ok = ['application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'application/msword'].includes(f.type)
    if (!ok) { setError('Please upload a PDF or DOCX file.'); return }
    setFile(f)
    setError(null)
  }

  const onDrop = (e) => {
    e.preventDefault(); setDragging(false)
    handleFile(e.dataTransfer.files[0])
  }

  const startStepCycle = () => {
    setStepIdx(0)
    let i = 0
    intervalRef.current = setInterval(() => {
      i = Math.min(i + 1, STEPS.length - 1)
      setStepIdx(i)
      if (i === STEPS.length - 1) clearInterval(intervalRef.current)
    }, 6000)
  }

  const handleAnalyze = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    startStepCycle()
    try {
      const result = await analyzeContract(file, partyA, partyB)
      clearInterval(intervalRef.current)
      navigate(`/report/${result.analysis_id}`, { state: result })
    } catch (err) {
      clearInterval(intervalRef.current)
      setError(err.response?.data?.detail || 'Analysis failed. Check your API key and try again.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="main-content">
        <div className="page-header">
          <h1>Analyzing Contract</h1>
          <p>Please wait — Gemini is reviewing your contract against the CUAD taxonomy</p>
        </div>
        <div className="page-body">
          <div className="loading-overlay">
            <div className="spinner" />
            <div className="progress-steps">
              {STEPS.map((s, i) => (
                <div
                  key={i}
                  className={`step ${i < stepIdx ? 'done' : i === stepIdx ? 'active' : ''}`}
                >
                  <span>{i < stepIdx ? '✓' : i === stepIdx ? '→' : '○'}</span>
                  {s}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="main-content">
      <div className="page-header">
        <h1>Analyze a Contract</h1>
        <p>Upload a PDF or DOCX contract — LexAI identifies risk clauses, missing protections, and per-party exposure</p>
      </div>

      <div className="page-body">
        <div style={{ maxWidth: 680 }}>

          {/* Upload zone */}
          <div
            className={`upload-zone ${dragging ? 'dragging' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => !file && fileRef.current.click()}
          >
            <input
              ref={fileRef} type="file"
              accept=".pdf,.doc,.docx"
              onChange={(e) => handleFile(e.target.files[0])}
            />

            {file ? (
              <div>
                <div className="flex items-center justify-between" style={{ background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', padding: '12px 16px' }}>
                  <div className="flex items-center gap-2">
                    <FileText size={20} color="var(--accent)" />
                    <div>
                      <div style={{ fontWeight: 500, fontSize: '0.9rem' }}>{file.name}</div>
                      <div className="text-muted text-xs">{(file.size / 1024).toFixed(0)} KB</div>
                    </div>
                  </div>
                  <button
                    className="btn btn-ghost"
                    style={{ padding: '4px 8px' }}
                    onClick={(e) => { e.stopPropagation(); setFile(null) }}
                  >
                    <X size={14} />
                  </button>
                </div>
                <p style={{ marginTop: 12, fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                  Click to change file
                </p>
              </div>
            ) : (
              <>
                <div className="upload-icon">
                  <UploadIcon size={40} />
                </div>
                <h3>Drop your contract here</h3>
                <p>PDF or DOCX · NDA, SaaS agreement, service contract, employment agreement</p>
                <button
                  className="btn btn-ghost"
                  style={{ marginTop: 16 }}
                  onClick={(e) => { e.stopPropagation(); fileRef.current.click() }}
                >
                  Browse files
                </button>
              </>
            )}
          </div>

          {/* Party names */}
          <div className="card mt-4">
            <div className="card-title">Party names (optional)</div>
            <div className="grid-2">
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                  Party A — You / Your company
                </label>
                <input
                  type="text"
                  placeholder="e.g. Acme Startup Pvt Ltd"
                  value={partyA}
                  onChange={(e) => setPartyA(e.target.value)}
                  style={{
                    width: '100%', padding: '8px 12px',
                    background: 'var(--bg-base)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-primary)',
                    fontSize: '0.875rem',
                    fontFamily: 'var(--font-sans)',
                    outline: 'none',
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                  Party B — Counterparty
                </label>
                <input
                  type="text"
                  placeholder="e.g. BigVendor Inc"
                  value={partyB}
                  onChange={(e) => setPartyB(e.target.value)}
                  style={{
                    width: '100%', padding: '8px 12px',
                    background: 'var(--bg-base)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-primary)',
                    fontSize: '0.875rem',
                    fontFamily: 'var(--font-sans)',
                    outline: 'none',
                  }}
                />
              </div>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginTop: 12, padding: '10px 14px', background: 'var(--red-dim)', border: '1px solid var(--red)', borderRadius: 'var(--radius-sm)', fontSize: '0.85rem', color: 'var(--red)' }}>
              <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
              {error}
            </div>
          )}

          {/* Analyze button */}
          <button
            className="btn btn-primary w-full mt-4"
            style={{ justifyContent: 'center', padding: '12px' }}
            disabled={!file || loading}
            onClick={handleAnalyze}
          >
            Analyze Contract
          </button>

          {/* Info */}
          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 10, textAlign: 'center' }}>
            Analysis takes 15–30 seconds · Powered by Gemini 2.5 Flash · CUAD legal taxonomy
          </p>
        </div>
      </div>
    </div>
  )
}
