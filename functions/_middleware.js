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
  if (url.hostname !== "ucplan.org" && !response.headers.has("x-robots-tag")) {
    // Preview deployments (*.ucplan.pages.dev) serve real pages with no
    // canonical, so keep them out of search indexes. The production alias
    // already redirected above; ucplan.org itself never hits this branch.
    var previewHeaders = new Headers(response.headers);
    previewHeaders.set("x-robots-tag", "noindex");
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: previewHeaders,
    });
  }
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
