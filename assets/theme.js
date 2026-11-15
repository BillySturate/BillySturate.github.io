(() => {
  let theme;
  try { theme = localStorage.getItem('silas-theme'); } catch (_) {}
  const hour = new Date().getHours();
  document.documentElement.dataset.theme = theme === 'light' || theme === 'dark'
    ? theme
    : (hour >= 7 && hour < 19 ? 'light' : 'dark');
})();
