(() => {
  "use strict";
  const doc = document;
  const flags = (typeof window !== "undefined" && window.FEATURE_FLAGS) || {};

  if (!flags.ads_enabled) {
    return;
  }

  function readCookie(name) {
    try {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop().split(";").shift();
    } catch (_) {
      return null;
    }
    return null;
  }

  function csrfToken() {
    return readCookie("csrftoken") || "";
  }

  function hasAdsConsent() {
    try {
      const raw = readCookie("consent_status");
      if (!raw) return false;
      if (raw === "1" || raw === "true") return true;
      const parsed = JSON.parse(decodeURIComponent(raw));
      if (parsed && typeof parsed === "object") {
        if (parsed.ads === true) return true;
        if (parsed.all === true || parsed.accept_all === true) return true;
      }
    } catch (_) {
      /* ignore */
    }
    return false;
  }
  const consentGranted = hasAdsConsent();

  async function fetchJson(url, options = {}) {
    const res = await fetch(url, {
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken(),
        ...(options.headers || {}),
      },
      ...options,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  }

  async function trackImpression(slug, creativeId, meta = {}) {
    if (!consentGranted) return;
    try {
      await fetchJson(`/ads/api/impression/`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          placement: slug,
          creative: creativeId || "",
          context: meta.context || "",
          page_url: window.location.href,
          referrer: document.referrer || "",
        }),
      });
    } catch (_) {
      /* silent */
    }
  }

  function wireClickTracking(slot, slug, creativeId) {
    const clickLinks = slot.querySelectorAll("[data-ad-click], a[href]");
    clickLinks.forEach((el) => {
      el.addEventListener("click", async () => {
        if (!consentGranted) return;
        try {
          await fetchJson(`/ads/api/click/`, {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({
              placement: slug,
              creative: creativeId || "",
              page_url: window.location.href,
              referrer: document.referrer || "",
            }),
          });
        } catch (_) {
          /* silent */
        }
      });
    });
  }

  async function hydrateSlot(slot) {
    const slug = slot.getAttribute("data-ad-slot");
    if (!slug) return;
    try {
      const data = await fetchJson(`/ads/api/fill/?placement=${encodeURIComponent(slug)}`);
      if (!data.ok || !data.creative) return;
      const c = data.creative;
      const clickUrl = c.click_url || "#";
      if (c.type === "html" && c.html) {
        slot.innerHTML = c.html;
      } else if (c.image_url) {
        slot.innerHTML = `<a href="${clickUrl}" data-ad-click data-placement="${slug}" data-creative="${c.creative || ""}"><img src="${c.image_url}" alt="ad" class="mx-auto" /></a>`;
      } else {
        // native text fallback
        slot.innerHTML = `<a href="${clickUrl}" data-ad-click class="block text-sm text-primary-700 hover:text-primary-900">${c.title || "Sponsored"}</a>`;
      }
      wireClickTracking(slot, slug, c.creative || c.id || "");
      await trackImpression(slug, c.creative || c.id || "", {
        context: slot.getAttribute("data-context") || "",
      });
    } catch (err) {
      /* silent */
    }
  }

  function mountAds() {
    const slots = doc.querySelectorAll("[data-ad-slot]");
    if (!slots.length) return;

    // Lazy-load when visible
    const obs = "IntersectionObserver" in window ? new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          hydrateSlot(entry.target);
          obs.unobserve(entry.target);
        }
      });
    }, { rootMargin: "100px" }) : null;

    slots.forEach((slot) => {
      if (obs) {
        obs.observe(slot);
      } else {
        hydrateSlot(slot);
      }
    });
  }

  if (doc.readyState === "loading") {
    doc.addEventListener("DOMContentLoaded", mountAds);
  } else {
    mountAds();
  }
})();
