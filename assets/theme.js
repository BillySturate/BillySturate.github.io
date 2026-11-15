(() => {
  let theme;
  try { theme = localStorage.getItem('silas-theme'); } catch (_) {}
  document.documentElement.dataset.theme = theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
})();
