// static/js/consent-banner-loader.js
(function () {
  "use strict";
  try {
    fetch("/consent/banner/", { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("no-banner");
        return r.text();
      })
      .then(function (html) {
        var el = document.getElementById("consent-banner");
        if (el && html && html.trim()) el.innerHTML = html;
      })
      .catch(function (e) {
        // do not break page functionality; log for diagnostics
        if (window.console && window.console.warn) {
          console.warn("consent banner load failed", e);
        }
      });
  } catch (e) {
    if (window.console && window.console.warn) console.warn("consent loader failure", e);
  }
})();
