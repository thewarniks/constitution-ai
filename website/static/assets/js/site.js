// Small site-wide behaviour for the Constitution Ai website.
(() => {
  "use strict";

  // Contact forms post to /api/contact (saved on the server for the site owner).
  document.querySelectorAll(".js-contact-form").forEach((form) => {
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const statusEl = form.querySelector(".form-status");
      const button = form.querySelector("button[type=submit]");
      if (window.CA_STATIC) {
        // The GitHub Pages copy has no server to receive messages.
        statusEl.textContent = "This is the static preview of the site, so the form can't send messages. It works when the site runs on the Python server.";
        statusEl.className = "form-status text-body-3 is-error";
        return;
      }
      const data = Object.fromEntries(new FormData(form).entries());
      if (!data.name?.trim() || !data.contact?.trim() || !data.message?.trim()) {
        statusEl.textContent = "Please fill in all three fields.";
        statusEl.className = "form-status text-body-3 is-error";
        return;
      }
      button.disabled = true;
      statusEl.textContent = "Sending…";
      statusEl.className = "form-status text-body-3";
      try {
        const res = await fetch("/api/contact", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(data),
        });
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.error?.message || res.statusText);
        form.reset();
        statusEl.textContent = "Thanks! Your message has been received.";
        statusEl.className = "form-status text-body-3 is-ok";
      } catch (err) {
        statusEl.textContent = `Couldn't send your message: ${err.message}`;
        statusEl.className = "form-status text-body-3 is-error";
      } finally {
        button.disabled = false;
      }
    });
  });
})();
