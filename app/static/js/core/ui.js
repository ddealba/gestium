(function () {
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
      const el = document.querySelector('[data-kbd-focus="search"]');
      if (el) { e.preventDefault(); el.focus(); }
    }
    if (e.key === "Escape") {
      closeAllDropdowns();
      closeAllDrawers();
    }
  });

  function closeAllDropdowns() {
    document.querySelectorAll("[data-dropdown].is-open").forEach(d => d.classList.remove("is-open"));
  }

  document.addEventListener("click", (e) => {
    const trigger = e.target.closest("[data-dropdown-trigger]");
    const dropdown = e.target.closest("[data-dropdown]");
    if (trigger && dropdown) {
      e.preventDefault();
      const isOpen = dropdown.classList.contains("is-open");
      closeAllDropdowns();
      if (!isOpen) dropdown.classList.add("is-open");
      return;
    }
    if (!dropdown) closeAllDropdowns();
  });

  function toast(title, message) {
    const stack = document.querySelector("[data-toast-stack]");
    if (!stack) return;

    const node = document.createElement("div");
    node.className = "toast";
    node.innerHTML = `
      <div>
        <p class="t">${escapeHtml(title)}</p>
        <p class="m">${escapeHtml(message || "")}</p>
      </div>
      <button class="x" aria-label="Cerrar">✕</button>
    `;
    node.querySelector(".x").addEventListener("click", () => node.remove());
    stack.appendChild(node);
    setTimeout(() => { if (node.isConnected) node.remove(); }, 4000);
  }

  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-toast]");
    if (!t) return;
    toast("Info", t.getAttribute("data-toast"));
  });

  function closeAllDrawers() {
    document.querySelectorAll(".backdrop.is-open").forEach(b => b.classList.remove("is-open"));
    document.body.style.overflow = "";
  }

  window.GestiumUI = window.GestiumUI || {};
  window.GestiumUI.openDrawer = function (selector) {
    const backdrop = document.querySelector(selector);
    if (!backdrop) return;
    backdrop.classList.add("is-open");
    document.body.style.overflow = "hidden";
  };
  window.GestiumUI.closeDrawer = function (selector) {
    const backdrop = document.querySelector(selector);
    if (!backdrop) return;
    backdrop.classList.remove("is-open");
    document.body.style.overflow = "";
  };

  document.addEventListener("click", (e) => {
    const openBtn = e.target.closest("[data-drawer-open]");
    if (openBtn) {
      window.GestiumUI.openDrawer(openBtn.getAttribute("data-drawer-open"));
      return;
    }
    const closeBtn = e.target.closest("[data-drawer-close]");
    if (closeBtn) {
      window.GestiumUI.closeDrawer(closeBtn.getAttribute("data-drawer-close"));
      return;
    }
    const backdrop = e.target.classList?.contains("backdrop") ? e.target : null;
    if (backdrop && backdrop.classList.contains("is-open")) {
      backdrop.classList.remove("is-open");
      document.body.style.overflow = "";
    }
  });

  function escapeHtml(str) {
    return (str || "").replace(/[&<>"']/g, (m) => ({
      "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
    }[m]));
  }
})();
