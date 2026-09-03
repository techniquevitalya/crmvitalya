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
})();
