# Free pdufa.bio email alerts: DRAFT for David's review

Status: **draft on branch `claude/project-thread-g9sjox`. Not merged, not live, nothing sent, no accounts opened.**
Why a draft: it collects people's email addresses and needs legal pages, so David reviews it first.
The privacy and terms text is a starting draft, not legal advice. Have a lawyer read it before launch.

Background: the Nov 18 monetization plan said to build a free alert list before charging, and to
open Pro only after about 500 alert subscribers (plus about 5K visitors a month and legal pages).

## What's in this draft

| Piece | File | Notes |
|---|---|---|
| Sign-up page and box | `pdufa_site_src/alerts/index.html` | Email, weekly or weekly plus decision-day, consent box, honeypot. Also shows confirm and unsubscribe results. `noindex` until launch. |
| Sign-up API | `pdufa_site_src/api/alerts/subscribe.mjs` | Double opt-in: stores a pending record for 48h and sends one confirmation email. Same answer whether or not the address is already subscribed. Rate-limited per address. |
| Confirm API | `pdufa_site_src/api/alerts/confirm.mjs` | The click that actually subscribes someone. |
| Unsubscribe API | `pdufa_site_src/api/alerts/unsubscribe.mjs` | One click. Supports the mail app's own unsubscribe button (RFC 8058). Deletes the record outright. The footer link opens a one-button page so mail scanners can't unsubscribe people. |
| Shared helpers | `pdufa_site_src/api/_alerts.mjs` | Everything is off unless `ALERTS_LIVE=1`. |
| Weekly email | `alerts/templates/digest.html`, `digest.txt` | Plain, no tracking pixels, no images. |
| Renderer | `alerts/render_digest.py` | Builds the email from the site's own `calendar.ics` and decision pages. Renders only, sends nothing. Refuses to output if the email's own words drift into prediction or advice. |
| Sample | `alerts/preview/digest_2026-11-22.html` and `.txt` | This week's real data: 6 decisions recorded, 3 goal dates ahead. |
| Privacy policy | `pdufa_site_src/privacy/index.html` | Draft. |
| Terms of use | `pdufa_site_src/terms/index.html` | Draft. Data licence matches the CC BY 4.0 the datasets already declare. |
| About: who runs it, contact | `pdufa_site_src/about/index.html` | Draft section between `ABOUT-DRAFT` markers, filled Nov 27 from your Nov 25 reply to STAT (name, background, why Odin stays off the site, holdings line). Only the contact email is still a placeholder. |

## Email provider: Resend (no account opened)

The site already uses Resend for Pro sign-in links (`api/auth/request.mjs`, `RESEND_API_KEY`), so alerts
reuse it. The list itself lives in Vercel KV, which the site already uses, so the list is pdufa.bio's,
not a vendor's, and can move to another sender later.

Resend's limits, read from resend.com on 2026-11-22:
- Free: 3,000 emails a month and 100 a day. Enough until about 100 subscribers, because the weekly
  digest goes to everyone on one day.
- Pro: $20 a month for 50,000 emails, no daily limit. Needed somewhere around 100 subscribers.
- Resend also has a marketing "Broadcasts" product, free up to 1,000 contacts. It could keep the
  weekly digest free longer, but it keeps the list in Resend. Not used in this draft.

Alternative if David would rather not run any of this: Buttondown hosts the list, sign-up and
unsubscribe for you, free for the first 100 subscribers (buttondown.com/pricing). Its price at 1,000
subscribers wasn't readable from the page.

## Before launch (David's decisions and inputs)

1. Fill the bracketed placeholders on the privacy and terms pages: operator's legal name, contact
   email, postal address, governing-law state, effective date, and the Pro section.
   The code already mentions `pro@pdufa.bio` and `support@pdufa.bio`; confirm which inbox is real.
   The same details go in the draft "Who runs it" and "Contact" sections of `/about` (added Nov 25
   after a journalist said the site has no information about who runs it). Show only what you choose.
2. A postal address must be in every email (US CAN-SPAM). A PO box or registered-agent address works.
3. In Resend: verify the pdufa.bio domain for `alerts@pdufa.bio` (SPF, DKIM, DMARC records), and keep
   open and click tracking off, because the privacy page promises no tracking.
4. In Vercel: set `ALERTS_SECRET` (32+ random characters) and then `ALERTS_LIVE=1`.
5. Flip `noindex,nofollow` to `index,follow` on `/alerts`, `/privacy`, `/terms`, remove the draft
   banners, add them to the sitemap, and add Privacy and Terms to the site-wide footer (that footer
   is generated, so it's a note for the pdufa builder, not a hand edit).
6. Put the small sign-up box on the calendar and decision pages (builder job, same reason).

## Not built yet (next step after review)

The sender: a weekly Vercel cron (Sunday evening ET) that runs the renderer's output to each confirmed
address in `alerts:list`, adds the per-person unsubscribe link and the `List-Unsubscribe` and
`List-Unsubscribe-Post: List-Unsubscribe=One-Click` headers, and sends through Resend in batches.
Decision-day emails for the second option would hook into the same daily data refresh.
Left out on purpose so nothing in this draft can send email.
