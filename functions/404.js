// Pretty URLs serve 404.html at /404 with status 200. Unknown paths already
// use that file as a real 404. This route returns the same document with
// status 404 so /404 is not an indexable URL. The file itself has no canonical.
export async function onRequest(context) {
  // ASSETS.fetch does not invoke Functions. If a runtime ever did, this header
  // stops the route from fetching itself again.
  if (context.request.headers.get("x-ucplan-asset") === "1") {
    return new Response("Not found", {
      status: 404,
      headers: {
        "content-type": "text/plain; charset=utf-8",
        "x-robots-tag": "noindex",
        "cache-control": "no-store",
      },
    });
  }
  var url = new URL(context.request.url);
  url.pathname = "/404";
  var asset = await context.env.ASSETS.fetch(new Request(url.toString(), {
    method: "GET",
    headers: { "x-ucplan-asset": "1" },
  }));
  var type = asset.headers.get("content-type") || "";
  if (asset.ok && type.indexOf("text/html") !== -1) {
    var headers = new Headers(asset.headers);
    headers.delete("content-length");
    headers.delete("content-encoding");
    headers.set("x-robots-tag", "noindex");
    headers.set("cache-control", "no-store");
    return new Response(asset.body, {
      status: 404,
      statusText: "Not Found",
      headers: headers,
    });
  }
  return new Response("Not found", {
    status: 404,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "x-robots-tag": "noindex",
      "cache-control": "no-store",
    },
  });
}
