document.addEventListener("DOMContentLoaded", () => {
  // Toggle between login and signup forms
  const loginForm = document.getElementById("login-form");
  const signupForm = document.getElementById("signup-form");
  const showSignup = document.getElementById("showSignup");
  const showLogin = document.getElementById("showLogin");

  if (showSignup) {
    showSignup.addEventListener("click", () => {
      loginForm.classList.remove("active");
      signupForm.classList.add("active");
    });
  }

  if (showLogin) {
    showLogin.addEventListener("click", () => {
      signupForm.classList.remove("active");
      loginForm.classList.add("active");
    });
  }

  // Theme toggle
  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("change", () => {
      document.body.classList.toggle("dark-theme", themeToggle.checked);
    });
  }
});
