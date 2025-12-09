
(function () {
  "use strict";

  const STORE_KEY = "machine_uuid";

  function uuidv4() {
    if (crypto && crypto.randomUUID) return crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      const r = (crypto.getRandomValues(new Uint8Array(1))[0] & 0xf) >> 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function setCookie(name, value, days) {
    const expires = new Date(Date.now() + (days || 365) * 864e5).toUTCString();
    document.cookie = `${name}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
  }

  function getCookie(name) {
    const m = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return m ? decodeURIComponent(m[2]) : null;
  }

  async function persistMachineUuid(uuid) {
    try {
      localStorage.setItem(STORE_KEY, uuid);
    } catch (e) {}
    try {
      setCookie(STORE_KEY, uuid, 365);
    } catch (e) {}
    try {
      if (window.indexedDB) {
        const req = indexedDB.open("device_identity", 1);
        req.onupgradeneeded = () => {
          req.result.createObjectStore("kv");
        };
        req.onsuccess = () => {
          const tx = req.result.transaction("kv", "readwrite");
          tx.objectStore("kv").put(uuid, STORE_KEY);
        };
      }
    } catch (e) {}
  }

  async function readMachineUuid() {
    try {
      const v = localStorage.getItem(STORE_KEY);
      if (v) return v;
    } catch (e) {}
    try {
      const c = getCookie(STORE_KEY);
      if (c) return c;
    } catch (e) {}
    try {
      if (window.indexedDB) {
        return await new Promise((resolve) => {
          const req = indexedDB.open("device_identity", 1);
          req.onupgradeneeded = () => req.result.createObjectStore("kv");
          req.onsuccess = () => {
            const tx = req.result.transaction("kv", "readonly");
            const getReq = tx.objectStore("kv").get(STORE_KEY);
            getReq.onsuccess = () => resolve(getReq.result || null);
            getReq.onerror = () => resolve(null);
          };
          req.onerror = () => resolve(null);
        });
      }
    } catch (e) {}
    return null;
  }

  async function getOrCreateMachineUuid(consentState) {
    // Require consent for security/fraud or analytics before persisting identifiers.
    const allowed =
      consentState &&
      (consentState.fraud_prevention ||
        consentState.account_protection ||
        consentState.security ||
        consentState.analytics);
    if (!allowed) return null;

    let uuid = await readMachineUuid();
    if (!uuid) {
      uuid = uuidv4();
      await persistMachineUuid(uuid);
    } else {
      // normalize across stores
      await persistMachineUuid(uuid);
    }
    return uuid;
  }

  async function collectEnhancedFingerprint(consentState) {
    // Only run if consent indicates security/fraud allowed
    const allowed =
      consentState &&
      (consentState.fraud_prevention || consentState.account_protection || consentState.security);
    if (!allowed) return { fingerprint_blob: null, fingerprint_hash: null };

    const blob = {
      ua: navigator.userAgent,
      language: navigator.language,
      platform: navigator.platform,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      screen: {
        width: screen.width,
        height: screen.height,
        colorDepth: screen.colorDepth,
      },
      hardware: {
        cores: navigator.hardwareConcurrency || null,
        memory: navigator.deviceMemory || null,
      },
      storage: {
        localStorage: !!window.localStorage,
        cookies: navigator.cookieEnabled,
      },
    };

    // Canvas hash (best-effort, non-PII)
    try {
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      ctx.textBaseline = "top";
      ctx.font = "14px 'Arial'";
      ctx.fillText("device-fp", 2, 2);
      const data = canvas.toDataURL();
      blob.canvas = data.slice(0, 128); // keep short
    } catch (e) {}

    const encoder = new TextEncoder();
    const data = encoder.encode(JSON.stringify(blob));
    const hashBuffer = await crypto.subtle.digest("SHA-256", data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");

    return { fingerprint_blob: blob, fingerprint_hash: hashHex };
  }

  async function attachToForms() {
    document.querySelectorAll("form").forEach((form) => {
      if (!form.method || form.method.toLowerCase() !== "post") return;
      form.addEventListener(
        "submit",
        async () => {
          try {
          const consentState =
            (window.Consent && window.Consent.getState && window.Consent.getState()) ||
            window.CONSENT_CATEGORIES ||
            null;
          const uuid = await getOrCreateMachineUuid(consentState);
          if (uuid && !form.querySelector('input[name="machine_uuid"]')) {
            const input = document.createElement("input");
            input.type = "hidden";
            input.name = "machine_uuid";
            input.value = uuid;
            form.appendChild(input);
          }
          if (form.dataset.collectFingerprint === "true") {
            const fp = await collectEnhancedFingerprint(consentState);
            if (fp.fingerprint_hash && !form.querySelector('input[name="fingerprint_hash"]')) {
              const hashInput = document.createElement("input");
              hashInput.type = "hidden";
              hashInput.name = "fingerprint_hash";
              hashInput.value = fp.fingerprint_hash;
              form.appendChild(hashInput);
            }
            if (fp.fingerprint_blob && !form.querySelector('input[name="fingerprint_blob"]')) {
              const blobInput = document.createElement("input");
              blobInput.type = "hidden";
              blobInput.name = "fingerprint_blob";
              blobInput.value = JSON.stringify(fp.fingerprint_blob || {});
              form.appendChild(blobInput);
            }
          }
        } catch (e) {
          /* non-fatal */
        }
      },
        { once: true }
      );
    });
  }

  window.DeviceIdentity = window.DeviceIdentity || {};
  window.DeviceIdentity.getMachineUuid = getOrCreateMachineUuid;
  window.DeviceIdentity.collectEnhancedFingerprint = collectEnhancedFingerprint;
  window.DeviceIdentity.init = attachToForms;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", attachToForms);
  } else {
    attachToForms();
  }
})();


