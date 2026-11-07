// Runs before first paint (external file: the CSP forbids inline script). Applies the saved theme, if any.
try { const t = localStorage.getItem("theme"); if (t === "light" || t === "dark") document.documentElement.setAttribute("data-theme", t); } catch (e) { /* no storage: follow the system */ }
