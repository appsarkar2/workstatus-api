// ===============================================================
// WorkStatus - {{TITLE}}
// ===============================================================

(function () {
  const app = document.getElementById("app");
  const user = getCurrentUser();

  function render() {
    const headerHtml = header({
      title: "{{TITLE}}",
      back: true,
      backUrl: "/dashboard.html"
    });

    const bodyHtml = `
      <section class="tasks-section">
        <h2 class="section-title">Coming soon</h2>
        ${emptyState("", "{{TITLE}}", "This page is being built")}
      </section>
    `;

    const navHtml = bottomNav("reports");

    app.innerHTML = headerHtml + bodyHtml + navHtml;
  }

  render();
})();