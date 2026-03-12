(() => {
  const path = window.location.pathname;
  if (path !== "/portal") return;

  const overdueCard = [...document.querySelectorAll('.ff-portal-kpi__label')].find(
    (item) => item.textContent.includes('Solicitudes vencidas'),
  );
  if (!overdueCard) return;

  const valueNode = overdueCard.parentElement.querySelector('.ff-portal-kpi__value');
  const overdue = Number(valueNode?.textContent || 0);
  if (overdue > 0) {
    overdueCard.parentElement.style.borderColor = 'rgba(180,35,24,.35)';
    overdueCard.parentElement.style.background = 'linear-gradient(180deg, rgba(180,35,24,.12), rgba(255,255,255,.98))';
  }
})();
