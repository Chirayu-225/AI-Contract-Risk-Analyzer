// src/components/Sidebar.jsx
import { useNavigate, useLocation } from 'react-router-dom'
import { Upload, History, Shield } from 'lucide-react'

const navItems = [
  { icon: Upload,  label: 'Analyze Contract', path: '/' },
  { icon: History, label: 'Past Analyses',    path: '/history' },
]

export default function Sidebar() {
  const navigate  = useNavigate()
  const location  = useLocation()

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="wordmark">Lex<span>AI</span></div>
        <div className="tagline">Contract Risk Intelligence</div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ icon: Icon, label, path }) => (
          <button
            key={path}
            className={`nav-item ${location.pathname === path ? 'active' : ''}`}
            onClick={() => navigate(path)}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </nav>

      <div style={{ padding: '16px', borderTop: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Shield size={14} color="var(--text-muted)" />
          <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>
            CUAD taxonomy · Gemini 2.5 Flash · Indian law context
          </span>
        </div>
      </div>
    </aside>
  )
}
