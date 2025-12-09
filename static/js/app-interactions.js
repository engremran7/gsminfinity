(() => {
  function refreshChart(button) {
    const url = button.getAttribute("data-chart-url");
    const targetId = button.getAttribute("data-chart-target");
    if (!url || !targetId) return;

    const target = document.getElementById(targetId);
    if (!target) return;

    const previous = target.innerHTML;
    target.innerHTML = '<div class="text-sm text-slate-500">Refreshing…</div>';

    fetch(url, { credentials: "same-origin" })
      .then((resp) => resp.text())
      .then((html) => {
        target.innerHTML = html || previous;
      })
      .catch(() => {
        target.innerHTML =
          '<div class="text-sm text-rose-600">Refresh failed. Please reload the page.</div>';
      });
  }

  document.addEventListener("click", (evt) => {
    const button = evt.target.closest(".js-chart-refresh");
    if (!button) return;
    evt.preventDefault();
    refreshChart(button);
  });
})();
