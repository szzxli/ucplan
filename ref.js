// Note: this ref allow-list must match the GoatCounter path function in the page loaders.
(function () {
  var allowedRefs = ["reddit", "transfer-center", "seo", "x", "x-bio"];
  var ref = new URLSearchParams(window.location.search).get("ref");
  if (!ref || allowedRefs.indexOf(ref) === -1) return;
  var toolLinks = [
    "https://szzxli.github.io/transfer-os/mobile/www/",
    "https://szzxli.github.io/UC-Course/web/"
  ];
  // Internal hop links: carry ?ref= to the intermediate page (/transfer-os,
  // /uc-course) so its own ref.js can attach it to the tool link.
  // Without this, ref is lost when a visitor goes home -> tool page -> tool.
  var internalLinks = ["/transfer-os", "/uc-course", "/uc-transfer-deadline"];
  document.querySelectorAll("a[href]").forEach(function (link) {
    var href = link.getAttribute("href");
    if (!href) return;
    var isToolLink = toolLinks.some(function (toolLink) {
      return href === toolLink || href.indexOf(toolLink) === 0;
    });
    var isInternalLink = internalLinks.some(function (path) {
      return href === path || href.indexOf(path + "?") === 0 || href.indexOf(path + "#") === 0;
    });
    if (!isToolLink && !isInternalLink) return;
    try {
      var url = new URL(href, window.location.href);
      url.searchParams.set("ref", ref);
      link.setAttribute("href", url.toString());
    } catch (e) {}
  });
})();
