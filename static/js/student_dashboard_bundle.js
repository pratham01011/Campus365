document.addEventListener("DOMContentLoaded", () => {
  console.log("Dashboard bundle loaded ✅");

  // === Theme Toggle ===
  const themeToggle = document.getElementById("themeToggle");

  if (localStorage.getItem("theme") === "dark") {
    document.body.classList.add("dark-theme");
    if (themeToggle) themeToggle.checked = true;
  }

  if (themeToggle) {
    themeToggle.addEventListener("change", () => {
      if (themeToggle.checked) {
        document.body.classList.add("dark-theme");
        localStorage.setItem("theme", "dark");
      } else {
        document.body.classList.remove("dark-theme");
        localStorage.setItem("theme", "light");
      }
    });
  }

  // === Smooth Scroll for Nav ===
  const navLinks = document.querySelectorAll("nav a");
  navLinks.forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      const targetId = link.getAttribute("href").substring(1);
      const targetSection = document.getElementById(targetId);
      if (targetSection) {
        window.scrollTo({ top: targetSection.offsetTop - 60, behavior: "smooth" });
      }
    });
  });

  // === Activity Form Demo ===
  const activityForm = document.querySelector("#activities form");
  if (activityForm) {
    activityForm.addEventListener("submit", (e) => {
      e.preventDefault();
      alert("✅ Activity submitted for approval!");
      activityForm.reset();
    });
  }
});
