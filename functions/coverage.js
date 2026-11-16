// Temporary. Delete this file when the real /coverage page is merged.
// The audit-fixes-coverage preview canonicalizes to https://ucplan.org/coverage,
// which 404s on production. A Pages Function overrides a static file of the
// same path, so this redirect would hide that page until this file is removed.
// 302 (not 301) so the redirect is not cached as permanent.
var HTML = "<!doctype html>\n" +
  "<html lang=\"en\">\n" +
  "<head>\n" +
  "<meta charset=\"utf-8\">\n" +
  "<title>UCPlan</title>\n" +
  "<meta name=\"robots\" content=\"noindex\">\n" +
  "<link rel=\"canonical\" href=\"https://ucplan.org/\">\n" +
  "</head>\n" +
  "<body>\n" +
  "<p><a href=\"https://ucplan.org/\">UCPlan</a></p>\n" +
  "</body>\n" +
  "</html>\n";

export function onRequest(context) {
  var incoming = new URL(context.request.url);
  var dest = new URL("https://ucplan.org/");
  dest.search = incoming.search;
  return new Response(HTML, {
    status: 302,
    headers: {
      Location: dest.toString(),
      "Content-Type": "text/html; charset=utf-8",
      "X-Robots-Tag": "noindex",
      "Cache-Control": "no-store",
    },
  });
}
