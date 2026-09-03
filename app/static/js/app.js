(function () {
  const root = document.documentElement;
  const toggle = document.getElementById("dark-toggle");

  if (localStorage.getItem("theme") === "dark") {
    root.classList.add("dark");
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      root.classList.toggle("dark");
      localStorage.setItem("theme", root.classList.contains("dark") ? "dark" : "light");
    });
  }

  let draggedId = null;

  document.querySelectorAll(".event-chip[draggable='true']").forEach(function (chip) {
    chip.addEventListener("dragstart", function () {
      draggedId = chip.dataset.eventId;
    });
  });

  document.querySelectorAll(".day-cell").forEach(function (cell) {
    cell.addEventListener("dragover", function (e) {
      if (!draggedId) return;
      e.preventDefault();
      cell.classList.add("drag-over");
    });
    cell.addEventListener("dragleave", function () {
      cell.classList.remove("drag-over");
    });
    cell.addEventListener("drop", function (e) {
      e.preventDefault();
      cell.classList.remove("drag-over");
      if (!draggedId) return;

      const id = draggedId;
      draggedId = null;

      fetch("/planning/event/" + id + "/move", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: cell.dataset.date,
          technicienId: parseInt(cell.dataset.technicienId, 10),
        }),
      }).then(function (resp) {
        if (resp.ok) {
          window.location.reload();
        } else {
          alert("Impossible de déplacer cette intervention.");
        }
      });
    });
  });
})();
