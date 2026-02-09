import { logout, me } from "/static/js/core/auth.js";

function bindLogout() {
  const logoutBtn = document.getElementById("logoutBtn");
  if (!logoutBtn) return;

  logoutBtn.addEventListener("click", (event) => {
    event.preventDefault();
    logout();
  });
}

async function populateTopbarEmail() {
  const emailNode = document.getElementById("topbarUserEmail");
  if (!emailNode) return;

  try {
    const user = await me();
    emailNode.textContent = user.email || "";
  } catch (_error) {
    emailNode.textContent = "";
  }
}

bindLogout();
populateTopbarEmail();
