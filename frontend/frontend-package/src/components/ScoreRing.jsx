// src/components/ScoreRing.jsx
export default function ScoreRing({ score }) {
  const cls = score >= 70 ? 'high' : score >= 40 ? 'medium' : 'low'
  const label = score >= 70 ? 'HIGH RISK' : score >= 40 ? 'MEDIUM RISK' : 'LOW RISK'

  // SVG ring
  const r = 52, cx = 64, cy = 64
  const circ = 2 * Math.PI * r
  const dash = circ * (score / 100)
  const strokeColor = score >= 70 ? 'var(--red)' : score >= 40 ? 'var(--orange)' : 'var(--green)'

  return (
    <div className="score-display">
      <svg width="128" height="128" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={cx} cy={cy} r={r} fill="none" stroke="var(--border)" strokeWidth="8" />
        <circle
          cx={cx} cy={cy} r={r} fill="none"
          stroke={strokeColor} strokeWidth="8"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
        <text
          x={cx} y={cy + 6}
          textAnchor="middle"
          style={{
            transform: 'rotate(90deg)',
            transformOrigin: `${cx}px ${cy}px`,
            fontFamily: 'var(--font-mono)',
            fontSize: '1.6rem',
            fontWeight: 500,
            fill: strokeColor,
          }}
        >
          {score}
        </text>
      </svg>
      <span className={`score-label score-${cls}`}>{label}</span>
    </div>
  )
}
