document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".alert").forEach(el => setTimeout(() => {
    try { bootstrap.Alert.getOrCreateInstance(el).close(); } catch(e) {}
  }, 4500));
});