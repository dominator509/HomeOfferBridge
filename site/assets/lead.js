/* Shared multi-step cash-offer lead form (home + city pages).
   Expects window.HOB_LEAD = { webhook, city, state, source, brandPhone }
   and DOM ids: offer, s1/s2/s3/sDone, addr/name/email/phone/consent/ack, etc.
*/
(function () {
  var cfg = window.HOB_LEAD || {};
  var WEBHOOK = cfg.webhook || "";
  var CITY = cfg.city || "";
  var STATE = cfg.state || "";
  var SRC = cfg.source || "home";
  var BRAND_PHONE = cfg.brandPhone || "";

  var CLIENT_REF =
    "cr_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);

  function $(id) {
    return document.getElementById(id);
  }

  function setMeter(pct, msg) {
    var fill = $("meterFill");
    var pctEl = $("meterPct");
    var msgEl = $("meterMsg");
    if (fill) fill.style.width = pct + "%";
    if (pctEl) pctEl.textContent = pct + "%";
    if (msg && msgEl) msgEl.textContent = msg;
  }

  function setProgress(step) {
    ["p1", "p2", "p3"].forEach(function (id, i) {
      var el = $(id);
      if (!el) return;
      el.classList.toggle("on", i < step);
      el.setAttribute("aria-current", i + 1 === step ? "step" : "false");
    });
  }

  function clearError(input) {
    if (!input) return;
    input.classList.remove("is-invalid");
    input.removeAttribute("aria-invalid");
    var hint = input.parentElement && input.parentElement.querySelector(".fieldhint.inline");
    if (hint) hint.remove();
  }

  function showError(input, message) {
    if (!input) return;
    clearError(input);
    input.classList.add("is-invalid");
    input.setAttribute("aria-invalid", "true");
    var hint = document.createElement("p");
    hint.className = "fieldhint inline";
    hint.textContent = message;
    input.parentElement.appendChild(hint);
    input.focus();
  }

  function validEmail(v) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  }

  function post(payload) {
    try {
      if (WEBHOOK && WEBHOOK.indexOf("http") === 0) {
        fetch(WEBHOOK, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          keepalive: true,
        }).catch(function () {});
      }
    } catch (e) {}
  }

  function showStep(id) {
    ["s1", "s2", "s3", "sDone"].forEach(function (sid) {
      var el = $(sid);
      if (el) el.style.display = sid === id ? "block" : "none";
    });
  }

  window.next = function next() {
    var addr = $("addr");
    var a = (addr && addr.value.trim()) || "";
    clearError(addr);
    if (a.length < 5) {
      showError(addr, "Enter a full street address so we can price the offer.");
      return;
    }
    showStep("s2");
    setProgress(2);
    var stepName = $("stepName");
    if (stepName) stepName.textContent = "How do we reach you?";
    setMeter(75, "Almost ready");
    var phone = $("phone");
    if (phone) phone.focus();
  };

  window.submitLead = function submitLead() {
    var nameEl = $("name");
    var emailEl = $("email");
    var phoneEl = $("phone");
    var addrEl = $("addr");
    var consentEl = $("consent");

    var name = (nameEl && nameEl.value.trim()) || "";
    var email = (emailEl && emailEl.value.trim()) || "";
    var phone = (phoneEl && phoneEl.value.trim()) || "";
    var addr = (addrEl && addrEl.value.trim()) || "";
    var consent = !!(consentEl && consentEl.checked);

    [nameEl, emailEl, phoneEl].forEach(clearError);
    var consentWrap = consentEl && consentEl.closest(".consent");
    if (consentWrap) consentWrap.classList.remove("is-invalid");

    if (name.length < 2) {
      showError(nameEl, "Please enter your name.");
      return;
    }
    if (!validEmail(email)) {
      showError(emailEl, "Enter a valid email so we can send your offer.");
      return;
    }
    if (phone.replace(/\D/g, "").length < 7) {
      showError(phoneEl, "Enter a working phone number.");
      return;
    }
    if (!consent) {
      if (consentWrap) consentWrap.classList.add("is-invalid");
      if (consentEl) consentEl.focus();
      return;
    }

    post({
      client_ref: CLIENT_REF,
      event: "lead",
      name: name,
      email: email,
      address: addr,
      phone: phone,
      city: CITY,
      state: STATE,
      source: SRC,
      consent: consent,
      ts: new Date().toISOString(),
      page: location.href,
    });

    showStep("s3");
    setProgress(3);
    var stepName = $("stepName");
    if (stepName) stepName.textContent = "Condition & disclosures";
    setMeter(90, "One quick step");
  };

  window.submitDisclosure = function submitDisclosure() {
    var cond = (document.querySelector('input[name="cond"]:checked') || {}).value;
    var ackEl = $("ack");
    var ackd = !!(ackEl && ackEl.checked);
    var condErr = $("condErr");
    var ackErr = $("ackErr");
    if (condErr) condErr.style.display = cond ? "none" : "block";
    if (ackErr) ackErr.style.display = ackd ? "none" : "block";
    if (!cond || !ackd) {
      if (!cond) {
        var grid = $("condgrid");
        if (grid) grid.scrollIntoView({ behavior: "smooth", block: "nearest" });
      } else if (ackEl) ackEl.focus();
      return;
    }
    var issues = Array.prototype.slice
      .call(document.querySelectorAll('input[name="issue"]:checked'))
      .map(function (i) {
        return i.value;
      });
    var disclose = $("disclose");
    post({
      client_ref: CLIENT_REF,
      event: "enrich",
      city: CITY,
      state: STATE,
      source: SRC,
      self_rated_condition: cond,
      disclosed_issues: issues,
      disclosure_text: (disclose && disclose.value.trim()) || "",
      disclosure_ack: true,
      ts: new Date().toISOString(),
    });
    showStep("sDone");
    setProgress(3);
    var stepName = $("stepName");
    if (stepName) stepName.textContent = "Submitted";
    setMeter(100, "Offer on the way");
    var mob = $("mobcta");
    if (mob) mob.classList.add("hide");
  };

  // Address meter + clear errors on input
  var addr = $("addr");
  if (addr) {
    addr.addEventListener("input", function () {
      clearError(addr);
      setMeter(this.value.trim().length > 4 ? 60 : 40, "Offer readiness");
    });
  }
  ["name", "email", "phone"].forEach(function (id) {
    var el = $(id);
    if (el) el.addEventListener("input", function () { clearError(el); });
  });
  var consent = $("consent");
  if (consent) {
    consent.addEventListener("change", function () {
      var wrap = consent.closest(".consent");
      if (wrap) wrap.classList.remove("is-invalid");
    });
  }

  // Consent expand/collapse
  document.querySelectorAll("[data-consent-toggle]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      var extra = btn.parentElement.querySelector(".consent-extra");
      if (!extra) return;
      var open = extra.hasAttribute("hidden");
      if (open) extra.removeAttribute("hidden");
      else extra.setAttribute("hidden", "");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      btn.textContent = open ? "Hide details" : "Show full consent";
    });
  });

  // Sticky mobile CTA — hide when #offer is in view
  var offer = $("offer");
  var mobcta = $("mobcta");
  if (offer && mobcta && "IntersectionObserver" in window) {
    var io = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          mobcta.classList.toggle("hide", entry.isIntersecting);
        });
      },
      { root: null, threshold: 0.2 }
    );
    io.observe(offer);
  }

  // Year in footer
  var yr = $("yr");
  if (yr) yr.textContent = new Date().getFullYear();

  // Success copy phone swap if present
  var donePhone = document.querySelector("[data-brand-phone]");
  if (donePhone && BRAND_PHONE) donePhone.textContent = BRAND_PHONE;
})();
