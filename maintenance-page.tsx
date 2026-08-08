'use client';

import { useState, useRef, useEffect } from 'react';

// ─── CONFIGURATION ────────────────────────────────────────────────────────────
// Change these values before deploying:
const PASSCODE = 'odin2026';            // ← YOUR PASSCODE
const COOKIE_NAME = 'pdufa_access';
const COOKIE_MAX_AGE = 60 * 60 * 24 * 7; // 7 days

// ─── THE HAUNTING QUOTE ───────────────────────────────────────────────────────
// Pick one of these by updating QUOTE and ATTRIBUTION below.
// Or write your own.
//
// Option A — Rainer Maria Rilke
//   "The future enters into us, in order to transform itself in us,
//    long before it happens."
//
// Option B — William Gibson
//   "The sky above the port was the color of television,
//    tuned to a dead channel."
//
// Option C — Attributed to the Oracle at Delphi
//   "Know what is to come."
//
// Option D — T.S. Eliot, "Burnt Norton"
//   "What might have been and what has been
//    point to one end, which is always present."
//
// Option E — Heraclitus (fragment)
//   "Time is a game played beautifully by children."
//
// Option F — Wallace Stevens
//   "The only emperor is the emperor of ice-cream."
//    (for something wryly cryptic rather than solemn)
//
// Option G — ODIN (invented / in-universe)
//   "The data was always there.
//    You just needed a god to read it."
//
// Option H — Paul Valéry
//   "The future is not what it used to be."

const QUOTE = 'The data was always there.\nYou just needed a god to read it.';
const ATTRIBUTION = '— ODIN';
// ─────────────────────────────────────────────────────────────────────────────

export default function MaintenancePage() {
  const [input, setInput] = useState('');
  const [error, setError] = useState(false);
  const [shaking, setShaking] = useState(false);
  const [unlocked, setUnlocked] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Check if already authenticated
  useEffect(() => {
    const cookies = document.cookie.split(';');
    const access = cookies.find(c => c.trim().startsWith(`${COOKIE_NAME}=`));
    if (access) {
      window.location.replace('/');
    }
    inputRef.current?.focus();
  }, []);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (input.trim().toLowerCase() === PASSCODE.toLowerCase()) {
      // Set cookie and redirect
      document.cookie = `${COOKIE_NAME}=1; max-age=${COOKIE_MAX_AGE}; path=/; SameSite=Lax`;
      setUnlocked(true);
      setTimeout(() => {
        window.location.replace('/');
      }, 800);
    } else {
      setError(true);
      setShaking(true);
      setInput('');
      setTimeout(() => setShaking(false), 600);
      setTimeout(() => setError(false), 3000);
      inputRef.current?.focus();
    }
  }

  const lines = QUOTE.split('\n');

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&family=EB+Garamond:ital,wght@0,400;0,500;1,400&display=swap');

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
          background: #080808;
          color: #e8e8e0;
          font-family: 'Inter', system-ui, sans-serif;
          min-height: 100vh;
          overflow: hidden;
        }

        .bg-noise {
          position: fixed;
          inset: 0;
          background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E");
          pointer-events: none;
          z-index: 0;
        }

        .grain {
          position: fixed;
          inset: 0;
          background: radial-gradient(ellipse 80% 60% at 50% 40%, rgba(30,20,50,0.35) 0%, transparent 70%);
          pointer-events: none;
          z-index: 0;
        }

        .container {
          position: relative;
          z-index: 1;
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 2rem;
          gap: 0;
        }

        .sigil {
          font-size: 1.1rem;
          letter-spacing: 0.35em;
          color: rgba(255,255,255,0.18);
          text-transform: uppercase;
          font-weight: 400;
          margin-bottom: 3.5rem;
          user-select: none;
        }

        .quote-block {
          text-align: center;
          margin-bottom: 4rem;
          max-width: 520px;
        }

        .quote-text {
          font-family: 'EB Garamond', Georgia, serif;
          font-size: clamp(1.5rem, 3.5vw, 2.2rem);
          font-weight: 400;
          line-height: 1.55;
          color: rgba(232,232,224,0.92);
          letter-spacing: 0.01em;
          display: block;
          margin-bottom: 1.2rem;
        }

        .quote-attribution {
          font-family: 'Inter', sans-serif;
          font-size: 0.75rem;
          letter-spacing: 0.2em;
          color: rgba(255,255,255,0.25);
          text-transform: uppercase;
          font-weight: 300;
        }

        .divider {
          width: 1px;
          height: 40px;
          background: linear-gradient(to bottom, transparent, rgba(255,255,255,0.12), transparent);
          margin: 0 auto 3rem;
        }

        .gate-form {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 1rem;
          width: 100%;
          max-width: 280px;
        }

        .gate-label {
          font-size: 0.68rem;
          letter-spacing: 0.25em;
          color: rgba(255,255,255,0.22);
          text-transform: uppercase;
          font-weight: 400;
        }

        .gate-input-wrap {
          position: relative;
          width: 100%;
        }

        .gate-input {
          width: 100%;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: 3px;
          color: rgba(232,232,224,0.9);
          font-family: 'Inter', monospace;
          font-size: 0.9rem;
          letter-spacing: 0.15em;
          padding: 0.75rem 1rem;
          text-align: center;
          outline: none;
          transition: border-color 0.2s, background 0.2s;
          -webkit-text-security: disc;
        }

        .gate-input:focus {
          border-color: rgba(255,255,255,0.25);
          background: rgba(255,255,255,0.05);
        }

        .gate-input.error {
          border-color: rgba(220, 60, 60, 0.6);
          background: rgba(220, 60, 60, 0.05);
        }

        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          15%       { transform: translateX(-6px); }
          30%       { transform: translateX(6px); }
          45%       { transform: translateX(-4px); }
          60%       { transform: translateX(4px); }
          75%       { transform: translateX(-2px); }
          90%       { transform: translateX(2px); }
        }

        .shaking {
          animation: shake 0.5s ease-out;
        }

        .error-msg {
          font-size: 0.65rem;
          letter-spacing: 0.18em;
          color: rgba(220, 80, 80, 0.8);
          text-transform: uppercase;
          min-height: 1rem;
          transition: opacity 0.3s;
        }

        .gate-btn {
          background: transparent;
          border: 1px solid rgba(255,255,255,0.12);
          border-radius: 3px;
          color: rgba(232,232,224,0.55);
          cursor: pointer;
          font-family: 'Inter', sans-serif;
          font-size: 0.68rem;
          letter-spacing: 0.28em;
          padding: 0.65rem 1.8rem;
          text-transform: uppercase;
          transition: border-color 0.2s, color 0.2s, background 0.2s;
          font-weight: 400;
        }

        .gate-btn:hover {
          border-color: rgba(255,255,255,0.3);
          color: rgba(232,232,224,0.9);
          background: rgba(255,255,255,0.04);
        }

        .gate-btn:active {
          background: rgba(255,255,255,0.08);
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(6px); }
          to   { opacity: 1; transform: translateY(0); }
        }

        .unlocked-msg {
          font-size: 0.72rem;
          letter-spacing: 0.22em;
          color: rgba(140, 200, 140, 0.75);
          text-transform: uppercase;
          animation: fadeIn 0.3s ease-out;
        }

        .footer {
          position: fixed;
          bottom: 1.8rem;
          left: 50%;
          transform: translateX(-50%);
          font-size: 0.6rem;
          letter-spacing: 0.22em;
          color: rgba(255,255,255,0.1);
          text-transform: uppercase;
          white-space: nowrap;
          user-select: none;
        }
      `}</style>

      <div className="bg-noise" aria-hidden />
      <div className="grain" aria-hidden />

      <main className="container">
        <div className="sigil">PDUFA.BIO</div>

        <div className="quote-block">
          <span className="quote-text">
            {lines.map((line, i) => (
              <span key={i}>
                {line}
                {i < lines.length - 1 && <br />}
              </span>
            ))}
          </span>
          <span className="quote-attribution">{ATTRIBUTION}</span>
        </div>

        <div className="divider" aria-hidden />

        {!unlocked ? (
          <form className="gate-form" onSubmit={handleSubmit} autoComplete="off">
            <label className="gate-label" htmlFor="passcode">
              Access required
            </label>
            <div className={`gate-input-wrap ${shaking ? 'shaking' : ''}`}>
              <input
                ref={inputRef}
                id="passcode"
                type="password"
                className={`gate-input ${error ? 'error' : ''}`}
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="· · · · · · · ·"
                autoComplete="off"
                spellCheck={false}
              />
            </div>
            <div className="error-msg">
              {error ? 'Access denied.' : '\u00A0'}
            </div>
            <button type="submit" className="gate-btn">
              Enter
            </button>
          </form>
        ) : (
          <div className="unlocked-msg">Access granted — entering</div>
        )}
      </main>

      <footer className="footer">© 2026 PDUFA.BIO — All systems offline</footer>
    </>
  );
}
