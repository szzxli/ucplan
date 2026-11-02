# UCPlan brand site

Brand entry for ucplan.org: one homepage plus two module pages
(Transfer-OS and UC Course Planner), with a static FAQ and a support
section. The two tools themselves live in their own repositories;
this site only links out to them.

- `index.html` — brand home: hero, two tool cards, how it works,
  free/Pro note, FAQ, support.
- `transfer-os.html` — Transfer-OS module page.
- `uc-course.html` — UC Course Planner module page.
- `manifest.webmanifest`, `sw.js`, `app.js` — PWA shell.
  Bump the `CACHE` name in `sw.js` on every release so returning
  visitors never get a stale version.

Content rules (do not break these):

- Never claim UCPlan is official or affiliated with UC or ASSIST.
- Never promise or predict admission.
- TAG six: Davis, Irvine, Merced, Riverside, Santa Barbara, Santa Cruz.
  UCLA, Berkeley, and San Diego do not offer TAG.
- No prices on the site. Pro is announced, not priced.
- Never claim nonprofit status.
- Support covers tool problems only, not personal transfer advising.
- Support email address is not decided yet — the site says
  "Email support is coming soon" and must not invent an address.

Deployment: this repository is connected to Cloudflare Pages.
The ucplan.org custom domain is wired only after explicit approval;
until then the site lives on its pages.dev URL.
