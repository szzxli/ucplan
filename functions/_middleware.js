// The production Pages alias (ucplan.pages.dev) serves the same site as
// https://ucplan.org. Send it to the custom domain. Branch and commit
// previews are other hostnames (*.ucplan.pages.dev) and stay put.
var PRODUCTION_ALIAS = "ucplan.pages.dev";

export async function onRequest(context) {
  var url = new URL(context.request.url);
  if (url.hostname === PRODUCTION_ALIAS) {
    url.hostname = "ucplan.org";
    url.protocol = "https:";
    return Response.redirect(url.toString(), 301);
  }

  var response = await context.next();
  if (response.status !== 404 || response.headers.has("x-robots-tag")) {
    return response;
  }
  var headers = new Headers(response.headers);
  headers.set("x-robots-tag", "noindex");
  return new Response(response.body, {
    status: 404,
    statusText: response.statusText || "Not Found",
    headers: headers,
  });
}
