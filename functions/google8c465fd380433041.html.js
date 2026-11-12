// Google Search Console verification for ucplan.org.
// Cloudflare Pages 308-redirects *.html to the extensionless path, so this
// Function serves the token at the exact URL Google checks, with 200.
export function onRequest() {
  return new Response("google-site-verification: google8c465fd380433041.html\n", {
    status: 200,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
