// Hand-drawn SVG sea creatures for the crew (no image generation, no emoji).
import type { AgentKey } from './api'

interface Props {
  agent: AgentKey
  size?: number
  color: string
}

const Eye = ({ x, y, r = 4 }: { x: number; y: number; r?: number }) => (
  <g>
    <circle cx={x} cy={y} r={r} fill="#fff" />
    <circle cx={x + r * 0.25} cy={y + r * 0.1} r={r * 0.55} fill="#0b1d33" />
    <circle cx={x + r * 0.45} cy={y - r * 0.3} r={r * 0.2} fill="#fff" />
  </g>
)

function Whale({ c }: { c: string }) {
  return (
    <g>
      <path d="M14 58 C14 34 38 24 60 28 C78 31 86 44 86 56 C86 70 72 78 52 78 C32 78 14 72 14 58 Z" fill={c} />
      <path d="M22 66 C34 76 66 78 82 64 C76 74 62 79 50 79 C36 79 26 74 22 66 Z" fill="#eaf3ff" opacity=".85" />
      <path d="M84 52 C92 44 96 38 98 30 C92 34 88 36 84 36 C88 42 88 48 84 52 Z" fill={c} />
      <path d="M84 52 C92 58 96 64 97 72 C91 66 87 64 83 62 Z" fill={c} />
      <Eye x={32} y={50} r={5} />
      <path d="M22 62 Q30 66 38 62" stroke="#0b1d33" strokeWidth="2" fill="none" strokeLinecap="round" />
      <g className="spout">
        <path d="M44 26 C42 18 38 14 34 12 M44 26 C46 18 50 14 54 12 M44 26 L44 14" stroke="#bfe4ff" strokeWidth="3" fill="none" strokeLinecap="round" />
      </g>
      <circle cx="58" cy="44" r="3" fill="#fff" opacity=".35" />
      <circle cx="66" cy="50" r="2" fill="#fff" opacity=".3" />
    </g>
  )
}

function Octopus({ c }: { c: string }) {
  return (
    <g>
      {[18, 32, 46, 60, 74].map((x, i) => (
        <path
          key={x}
          className={`arm arm-${i}`}
          d={`M${x + 6} 58 C${x - 2} 70 ${x + 12} 76 ${x + 4} 90`}
          stroke={c}
          strokeWidth="8"
          fill="none"
          strokeLinecap="round"
        />
      ))}
      <path d="M20 56 C18 28 36 12 52 12 C70 12 84 28 82 56 C70 64 32 64 20 56 Z" fill={c} />
      <circle cx="40" cy="24" r="4" fill="#fff" opacity=".3" />
      <Eye x={40} y={40} r={6} />
      <Eye x={62} y={40} r={6} />
      <path d="M44 52 Q51 57 58 52" stroke="#0b1d33" strokeWidth="2" fill="none" strokeLinecap="round" />
      <circle cx="33" cy="49" r="3" fill="#ff5c7a" opacity=".5" />
      <circle cx="69" cy="49" r="3" fill="#ff5c7a" opacity=".5" />
    </g>
  )
}

function Turtle({ c }: { c: string }) {
  return (
    <g>
      <ellipse cx="22" cy="70" rx="10" ry="6" fill="#a8e6c9" transform="rotate(-25 22 70)" />
      <ellipse cx="76" cy="72" rx="10" ry="6" fill="#a8e6c9" transform="rotate(25 76 72)" />
      <ellipse cx="22" cy="48" rx="11" ry="6" fill="#a8e6c9" transform="rotate(25 22 48)" />
      <ellipse cx="80" cy="48" rx="11" ry="6" fill="#a8e6c9" transform="rotate(-25 80 48)" className="flipper" />
      <circle cx="88" cy="58" r="11" fill="#a8e6c9" />
      <Eye x={91} y={55} r={3.5} />
      <path d="M86 63 Q90 66 94 63" stroke="#0b1d33" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <path d="M18 62 C18 34 38 26 52 26 C68 26 84 36 82 62 Z" fill={c} />
      <path d="M50 30 L62 40 L58 54 L42 54 L38 40 Z" fill="#000" opacity=".14" />
      <path d="M38 40 L26 46 L28 60 M62 40 L74 46 L74 60 M42 54 L40 62 M58 54 L60 62" stroke="#000" opacity=".14" strokeWidth="2.5" fill="none" />
      <path d="M16 62 L84 62" stroke="#2e9e6b" strokeWidth="4" strokeLinecap="round" />
    </g>
  )
}

function Crab({ c }: { c: string }) {
  return (
    <g>
      <path d="M58 70 C40 74 20 66 20 48 C20 30 36 20 50 24 C64 28 68 40 60 48 C54 54 44 50 46 42 C48 36 54 38 54 42" stroke="#f6e2c4" strokeWidth="0" fill="#f3d9b1" />
      <path d="M58 70 C40 74 20 66 20 48 C20 30 36 20 50 24 C64 28 68 40 60 48 C54 54 44 50 46 42 C48 36 54 38 54 42" stroke="#c9a173" strokeWidth="3" fill="none" strokeLinecap="round" />
      <ellipse cx="66" cy="70" rx="18" ry="11" fill={c} />
      <path d="M62 60 L60 44 M72 60 L74 44" stroke={c} strokeWidth="3" />
      <Eye x={60} y={42} r={4} />
      <Eye x={74} y={42} r={4} />
      <g className="claw">
        <path d="M82 66 C92 60 96 50 92 44 C88 48 84 50 86 56 C82 52 84 46 88 42 C96 46 98 58 88 68 Z" fill={c} />
      </g>
      <path d="M52 78 L44 88 M60 80 L56 90 M74 80 L78 90 M80 78 L88 86" stroke={c} strokeWidth="3.5" strokeLinecap="round" />
      <path d="M60 72 Q66 76 72 72" stroke="#0b1d33" strokeWidth="1.8" fill="none" strokeLinecap="round" />
    </g>
  )
}

function Dolphin({ c }: { c: string }) {
  return (
    <g>
      <path d="M8 62 C20 40 46 30 70 36 C80 38 88 44 94 52 C88 52 84 54 80 58 C70 66 50 70 30 66 C22 72 14 78 6 80 C10 74 12 68 8 62 Z" fill={c} />
      <path d="M30 66 C46 70 66 66 78 58 C70 64 52 72 34 70 Z" fill="#e6fbff" opacity=".9" />
      <path d="M48 36 C50 26 56 20 64 18 C60 26 60 32 62 36 Z" fill={c} />
      <path d="M50 64 C52 72 48 78 42 82 C44 76 44 70 42 66 Z" fill={c} />
      <Eye x={74} y={46} r={4} />
      <path d="M82 54 Q88 56 92 53" stroke="#0b1d33" strokeWidth="1.8" fill="none" strokeLinecap="round" />
      <circle cx="40" cy="46" r="3" fill="#fff" opacity=".35" />
    </g>
  )
}

export function Creature({ agent, size = 72, color }: Props) {
  const body = {
    boss: <Whale c={color} />,
    inventory: <Octopus c={color} />,
    accounting: <Turtle c={color} />,
    facilities: <Crab c={color} />,
    customer_service: <Dolphin c={color} />,
  }[agent]
  return (
    <svg className={`creature creature-${agent}`} viewBox="0 0 100 100" width={size} height={size} aria-hidden="true">
      {body}
    </svg>
  )
}

/** A little clam that opens and shows its pearl once a ticket is resolved. */
export function Clam({ open, glowing, waiting }: { open: boolean; glowing?: boolean; waiting?: boolean }) {
  return (
    <svg viewBox="0 0 60 48" width="46" height="37" className={`clam ${open ? 'open' : ''} ${glowing ? 'glowing' : ''} ${waiting ? 'waiting' : ''}`} aria-hidden="true">
      <path d="M6 30 C6 42 54 42 54 30 Z" fill="#f2b5c4" />
      <path d="M8 31 L52 31" stroke="#d98aa0" strokeWidth="1.5" />
      <circle className="pearl" cx="30" cy="28" r="7" fill="url(#pearl)" />
      <g className="lid">
        <path d="M6 30 C6 12 54 12 54 30 Z" fill="#ffc9d6" />
        <path d="M30 14 L30 30 M20 16 L24 30 M40 16 L36 30 M12 22 L18 30 M48 22 L42 30" stroke="#e79cb0" strokeWidth="1.5" />
      </g>
      <defs>
        <radialGradient id="pearl" cx=".35" cy=".35">
          <stop offset="0" stopColor="#fff" />
          <stop offset=".6" stopColor="#f3f0ff" />
          <stop offset="1" stopColor="#c7c0ea" />
        </radialGradient>
      </defs>
    </svg>
  )
}

export function Chest({ shaking }: { shaking: boolean }) {
  return (
    <svg viewBox="0 0 100 80" width="92" height="74" className={`chest ${shaking ? 'shake' : ''}`} aria-hidden="true">
      <rect x="10" y="34" width="80" height="40" rx="6" fill="#8a5a2b" />
      <rect x="10" y="34" width="80" height="40" rx="6" fill="none" stroke="#5e3a17" strokeWidth="3" />
      <path d="M10 36 C10 14 90 14 90 36 Z" fill="#a46a33" stroke="#5e3a17" strokeWidth="3" />
      <rect x="44" y="30" width="12" height="16" rx="3" fill="#ffd166" stroke="#b8860b" strokeWidth="2" />
      <path d="M24 20 L24 72 M76 20 L76 72" stroke="#ffd166" strokeWidth="4" opacity=".85" />
      <circle cx="30" cy="30" r="5" fill="#ffd166" />
      <circle cx="40" cy="26" r="5" fill="#ffe08a" />
      <circle cx="62" cy="27" r="5" fill="#ffd166" />
      <circle cx="70" cy="31" r="4" fill="#ffe08a" />
    </svg>
  )
}
