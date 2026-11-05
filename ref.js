(function () {
  var allowedRefs = ["reddit", "transfer-center", "seo"];
  var ref = new URLSearchParams(window.location.search).get("ref");
  if (!ref || allowedRefs.indexOf(ref) === -1) return;
  var toolLinks = [
    "https://szzxli.github.io/transfer-os/mobile/www/",
    "https://szzxli.github.io/UC-Course/web/"
  ];
  document.querySelectorAll("a[href]").forEach(function (link) {
    var href = link.getAttribute("href");
    if (!href) return;
    var isToolLink = toolLinks.some(function (toolLink) {
      return href === toolLink || href.indexOf(toolLink) === 0;
    });
    if (!isToolLink) return;
    try {
      var url = new URL(href, window.location.href);
      url.searchParams.set("ref", ref);
      link.setAttribute("href", url.toString());
    } catch (e) {}
  });
})();
