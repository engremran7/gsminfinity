(() => {
  "use strict";

  if (!window.AUTH_IS_AUTHENTICATED) return;

  async function collectDevicePayload() {
    const nav = navigator || {};
    const scr = window.screen || {};

    function getGpu() {
      try {
        const canvas = document.createElement("canvas");
        const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
        if (!gl) return { vendor: "", renderer: "" };
        const dbg = gl.getExtension("WEBGL_debug_renderer_info");
        if (!dbg) return { vendor: "", renderer: "" };
        return {
          vendor: gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) || "",
          renderer: gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) || "",
        };
      } catch {
        return { vendor: "", renderer: "" };
      }
    }

    const gpu = getGpu();

    return {
      screen: scr.width && scr.height ? `${scr.width}x${scr.height}` : "",
      pixel_ratio: window.devicePixelRatio || "",
      timezone: (() => {
        try {
          return Intl.DateTimeFormat().resolvedOptions().timeZone || "";
        } catch {
          return "";
        }
      })(),
      cores: nav.hardwareConcurrency || "",
      device_memory: nav.deviceMemory || "",
      touch_points: nav.maxTouchPoints || 0,
      languages: (nav.languages || []).join(","),
      gpu_vendor: gpu.vendor,
      gpu_renderer: gpu.renderer,
    };
  }

  async function sendDevicePayload() {
    const payload = await collectDevicePayload();
    const csrftoken =
      document.querySelector('input[name="csrfmiddlewaretoken"]')?.value ||
      document.cookie.split("; ").find((row) => row.startsWith("csrftoken="))?.split("=")[1];

    try {
      await fetch("/devices/payload/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken || "",
        },
        credentials: "include",
        body: JSON.stringify(payload),
      });
    } catch {
      /* ignore */
    }
  }

  document.addEventListener("DOMContentLoaded", sendDevicePayload);
})();
