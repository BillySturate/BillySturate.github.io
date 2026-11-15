/* Blog only: retain owner-domain statistics and the existing manual theme switch. */
(() => {
  if (window.billyBlogRuntime) return;
  window.billyBlogRuntime = true;
  const officialHosts = new Set(['billysturate.top', 'www.billysturate.top']);
  let lastCountedPage = null;
  let sliderFixTimer = null;
  function fixFeaturedSlider() {
    const container = document.querySelector('#swiper_container');
    if (!container || container.dataset.billySliderFixed) return;
    let attempts = 0;
    clearInterval(sliderFixTimer);
    sliderFixTimer = setInterval(() => {
      if (!container.isConnected || ++attempts > 50) { clearInterval(sliderFixTimer); return; }
      const old = container.swiper;
      if (!old || !window.Swiper) return;
      // Recreate the archived fade transition after the responsive card has its final width.
      const initialSlide = old.realIndex || 0;
      old.destroy(true, true);
      const slider = new window.Swiper(container, {
        passiveListeners: true,
        spaceBetween: 30,
        effect: 'fade',
        fadeEffect: { crossFade: true },
        loop: true,
        initialSlide,
        autoplay: { disableOnInteraction: true, delay: 3000 },
        mousewheel: true,
        pagination: { el: container.querySelector('.blog-slider__pagination'), clickable: true },
      });
      container.onmouseenter = () => slider.autoplay.stop();
      container.onmouseleave = () => slider.autoplay.start();
      container.dataset.billySliderFixed = 'true';
      clearInterval(sliderFixTimer);
    }, 100);
  }
  function updateClock() {
    document.querySelectorAll('[data-blog-year]').forEach(el => { el.textContent = new Date().getFullYear(); });
    if (window.billyAutoTheme) window.billyAutoTheme();
  }
  function updatePage() {
    updateClock();
    if (document.querySelector('#home_top')) {
      fixFeaturedSlider();
      const greeting = document.querySelector('#author-info__sayhi');
      if (greeting && !greeting.dataset.billyGreeting) {
        greeting.dataset.billyGreeting = 'true';
        const setGreeting = () => { if (greeting.textContent !== 'Hi there! 👋') greeting.textContent = 'Hi there! 👋'; };
        new MutationObserver(setGreeting).observe(greeting, {childList:true,subtree:true,characterData:true});
        setGreeting();
      }
    }
    // Shared localhost / preview host counters are not this owner's traffic.
    // Never replace unavailable numbers with fixtures or an archived snapshot.
    const currentPage = location.pathname + location.search;
    if (lastCountedPage === currentPage) return;
    lastCountedPage = currentPage;
    const rows = document.querySelectorAll('[data-live-stat]');
    rows.forEach(el => { el.hidden = true; });
    if (!officialHosts.has(location.hostname)) return;
    document.querySelectorAll('[data-live-stat] .item-count').forEach(el => {
      el.textContent = '';
      const observer = new MutationObserver(() => {
        if (/^\d+$/.test(el.textContent.trim())) { el.closest('[data-live-stat]').hidden = false; observer.disconnect(); }
      });
      observer.observe(el, {childList:true, subtree:true, characterData:true});
      setTimeout(() => observer.disconnect(), 15000);
    });
    const script = document.createElement('script');
    script.src = 'https://busuanzi.ibruce.info/busuanzi/2.3/busuanzi.pure.mini.js';
    script.referrerPolicy = 'origin';
    script.async = true;
    script.onload = script.onerror = () => script.remove();
    document.head.appendChild(script);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', updatePage, {once:true});
  else updatePage();
  document.addEventListener('pjax:complete', updatePage);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) updateClock(); });
  setInterval(updateClock, 60000);
})();
