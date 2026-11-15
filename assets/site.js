const toggle = document.querySelector('.theme-toggle');
function updateLabel() {
  toggle?.setAttribute('aria-label', `Switch to ${document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'} mode`);
}
toggle?.addEventListener('click', () => {
  const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem('silas-theme', next); } catch (_) {}
  updateLabel();
});
updateLabel();
