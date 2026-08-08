import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// ─── MAINTENANCE MODE CONFIG ──────────────────────────────────────────────────
// Set MAINTENANCE_MODE = true to lock the site.
// Set MAINTENANCE_MODE = false to reopen (or just delete this file).
const MAINTENANCE_MODE = true;

// The cookie set by the maintenance page upon correct passcode entry
const COOKIE_NAME = 'pdufa_access';

// Route where the maintenance gate lives
const MAINTENANCE_PATH = '/maintenance';

// Paths that bypass the gate entirely (assets, API, etc.)
const BYPASS_PREFIXES = [
  '/_next/',
  '/favicon',
  '/robots',
  '/sitemap',
  '/api/',
  '/maintenance',     // the page itself must be reachable
];
// ─────────────────────────────────────────────────────────────────────────────

export function middleware(request: NextRequest) {
  if (!MAINTENANCE_MODE) return NextResponse.next();

  const { pathname } = request.nextUrl;

  // Always allow bypass paths (static assets, maintenance page itself, etc.)
  if (BYPASS_PREFIXES.some(prefix => pathname.startsWith(prefix))) {
    return NextResponse.next();
  }

  // Allow through if the user has the access cookie
  const accessCookie = request.cookies.get(COOKIE_NAME);
  if (accessCookie?.value === '1') {
    return NextResponse.next();
  }

  // Everything else → redirect to /maintenance
  const url = request.nextUrl.clone();
  url.pathname = MAINTENANCE_PATH;
  return NextResponse.redirect(url);
}

export const config = {
  // Run on all routes except Next.js internals and static files
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
