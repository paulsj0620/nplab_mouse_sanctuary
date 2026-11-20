// Same-origin adapter. App event handlers and analytical data stay in their own document.
(() => {
  const platform = location.pathname.startsWith('/singlecell/') ? 'singlecell' :
    location.pathname.startsWith('/results/') ? 'omics' : 'mouse';
  if (window.top === window) {
    location.replace(`/?platform=${platform}`);
    return;
  }
  const portal = window.top;
  const initial = portal.NPLabSession?.language || 'en';
  // Seed each app's existing preference before its translation script initializes.
  for (const key of ['mouse-sanctuary-language', 'omics-explorer-language', 'singlecell-explorer-language']) {
    try { localStorage.setItem(key, initial); } catch {}
  }
  document.documentElement.dataset.portalPlatform = platform;

  function applyLanguage(language) {
    if (!['en', 'ko'].includes(language)) return;
    const select = document.querySelector('#language-select, [data-language-select]');
    if (select && select.value !== language) {
      select.value = language;
      select.dispatchEvent(new Event('change', {bubbles: true}));
    }
    const toggle = document.querySelector(`[data-language="${language}"]`);
    if (toggle?.getAttribute('aria-pressed') !== 'true') toggle?.click();
  }

  let navigationTargets = [];
  let previousNavigation = '';
  function navigation() {
    const selectors = {
      mouse: '#workspace > header nav button[data-page]',
      omics: '.explorer-nav button[data-kind]',
      singlecell: '#stage a[data-value]'
    };
    navigationTargets = [...document.querySelectorAll(selectors[platform])].filter(element => {
      if (element.closest('[hidden]')) return false;
      for (let node = element; node && !node.matches('nav, #stage'); node = node.parentElement) {
        if (getComputedStyle(node).display === 'none') return false;
      }
      return true;
    });
    const items = navigationTargets.map((element, index) => ({
      id: String(index), label: element.textContent.trim(), disabled: Boolean(element.disabled),
      active: element.classList.contains('active') || element.parentElement.classList.contains('active') ||
        element.getAttribute('aria-pressed') === 'true'
    }));
    const signature = JSON.stringify(items);
    if (signature !== previousNavigation) {
      previousNavigation = signature;
      window.parent.postMessage({type: 'nplab-navigation', platform, items}, location.origin);
    }
  }

  function ready() {
    applyLanguage(portal.NPLabSession?.language || initial);
    navigation();
    const nativeHeader = document.querySelector('#workspace > header, .omics-header, header.top');
    if (nativeHeader) new MutationObserver(navigation).observe(nativeHeader, {
      subtree: true, childList: true, characterData: true, attributes: true,
      attributeFilter: ['class', 'hidden', 'style', 'aria-pressed', 'disabled']
    });
    document.addEventListener('languagechange', navigation);
    if (platform === 'mouse') {
      let opened = false;
      document.addEventListener('workspace-session-ready', () => {
        applyLanguage(portal.NPLabSession?.language || initial);
        navigation();
        if (!opened && new URLSearchParams(location.search).get('portalAccount') === '1') {
          opened = true;
          document.getElementById('my-account')?.click();
        }
      });
    }
    // The parent's cookie is checked server-side for every platform request.
    // This also returns to Portal when Mouse Sanctuary invalidates a session.
    const auth = document.getElementById('auth');
    if (auth) new MutationObserver(() => {
      if (!auth.hidden) window.parent.postMessage({type: 'nplab-expired'}, location.origin);
    }).observe(auth, {attributes: true, attributeFilter: ['hidden']});
  }
  window.addEventListener('message', event => {
    if (event.origin === location.origin && event.source === portal && event.data?.type === 'nplab-language') {
      applyLanguage(event.data.language);
      navigation();
    }
    if (event.origin === location.origin && event.source === portal && event.data?.type === 'nplab-select-tool') {
      navigationTargets[Number(event.data.id)]?.click();
      navigation();
    }
  });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ready);
  else ready();
})();
