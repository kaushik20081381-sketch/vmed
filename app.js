// Small shared behaviors: confirm dialogs on destructive actions, chart rendering helper.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("submit", function (e) {
      if (!confirm(el.getAttribute("data-confirm"))) {
        e.preventDefault();
      }
    });
  });
});

// Renders a Chart.js line chart for a lab test series inside a <canvas data-chart='...'>
function renderLabCharts() {
  document.querySelectorAll("canvas[data-chart]").forEach(function (canvas) {
    var payload = JSON.parse(canvas.getAttribute("data-chart"));
    var refRange = payload.reference_range;
    var datasets = [{
      label: payload.display_name + (payload.unit ? " (" + payload.unit + ")" : ""),
      data: payload.values,
      borderColor: "#1F6F78",
      backgroundColor: "rgba(31,111,120,0.12)",
      tension: 0.25,
      fill: true,
      pointRadius: 4,
    }];
    new Chart(canvas.getContext("2d"), {
      type: "line",
      data: { labels: payload.labels, datasets: datasets },
      options: {
        responsive: true,
        plugins: { legend: { display: true, position: "top" } },
        scales: {
          y: refRange ? { suggestedMin: Math.min(refRange[0], Math.min(...payload.values)),
                          suggestedMax: Math.max(refRange[1], Math.max(...payload.values)) } : {}
        }
      }
    });
  });
}
