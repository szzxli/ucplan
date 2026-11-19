# UCPlan brand site

Brand entry for ucplan.org: one homepage plus two module pages
(Transfer-OS and UC Course Planner), with a static FAQ and a support
section. The two tools themselves live in their own repositories;
this site only links out to them.

- `index.html` — brand home: hero, coverage lookup, Transfer-OS card, an "After you transfer"
  slot for UC Course Planner (students already at UC; UC Irvine, UC San Diego,
  and UC Santa Barbara, 22 majors), how it works, free/Pro note, FAQ, support.
  The homepage defaults to English.
- `coverage.html` — published lists: 50 community colleges, 108 Transfer-OS UC majors,
  and the 22 UC Course Planner majors, with the ASSIST data year for each UC.
- `transfer-os.html` — Transfer-OS module page.
- `uc-course.html` — UC Course Planner module page.
- `manifest.webmanifest`, `sw.js`, `app.js` — PWA shell.
  Bump the `CACHE` name in `sw.js` on every release so returning
  visitors never get a stale version.
- `i18n.js` + `lang/*.json` — language switcher. One button in the
  header opens a scrollable list: English, Español, 简体中文,
  繁體中文, 한국어, 日本語. The choice persists in localStorage
  (`ucplan.lang`). The homepage defaults to English until the visitor picks a language.
  On other translated pages, with no saved choice the browser language is used
  (zh-Hant/TW/HK → 繁體中文, other zh → 简体中文, es, ko, ja), else English. Page text is keyed with
  `data-i18n`; every key must exist in every language file. Translated pages use the
  `index.`, `tos.`, `cuc.`, `cov.`, or `tna.` key prefix.

Content rules (do not break these):

- Never claim UCPlan is official or affiliated with UC or ASSIST.
- Never promise or predict admission.
- TAG six: Davis, Irvine, Merced, Riverside, Santa Barbara, Santa Cruz.
  UCLA, Berkeley, and San Diego do not offer TAG.
- No prices on the site. Pro is announced, not priced.
- Never claim nonprofit status.
- Support covers tool problems only, not personal transfer advising.
- The support address stays plain text inside `<!--email_off-->` comments.
  Do not turn it into a `mailto:` link: Cloudflare would rewrite that into
  a `/cdn-cgi/l/email-protection` URL that 404s.

Deployment: this repository is connected to Cloudflare Pages.
The ucplan.org custom domain is wired only after explicit approval;
until then the site lives on its pages.dev URL.
