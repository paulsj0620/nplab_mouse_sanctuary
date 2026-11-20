'use strict';
const byId = id => document.getElementById(id);
const platforms = {
  home: {title: 'NPLab Portal', icon: '/hub/icons/portal.png'},
  mouse: {title: 'Mouse Sanctuary', icon: '/hub/icons/mouse.png', path: '/mouse/'},
  omics: {title: 'Omics Explorer', icon: '/hub/icons/omics.png'},
  singlecell: {title: 'Single Cell Explorer', icon: '/hub/icons/singlecell.png'}
};
let language = 'en';
let session;
let currentPlatform = 'home';
let previousUserId;
let saveSequence = 0;
try { language = localStorage.getItem('mouse-sanctuary-language') === 'ko' ? 'ko' : 'en'; } catch {}

async function api(path, options = {}) {
  const response = await fetch(path, {cache: 'no-store', ...options});
  const type = response.headers.get('Content-Type') || '';
  const data = type.includes('json') ? await response.json() : {error: await response.text()};
  if (!response.ok) {
    const error = new Error(data.error || 'Connection failed');
    error.status = response.status;
    throw error;
  }
  return data;
}

function applyLanguage() {
  document.documentElement.lang = language;
  byId('language-select').value = language;
  document.querySelectorAll('[data-en]').forEach(node => { node.textContent = node.dataset[language]; });
  document.querySelectorAll('#platform-nav [data-platform]').forEach(link => {
    const key = link.dataset.platform;
    link.setAttribute('aria-label', key === 'home' ? (language === 'ko' ? '홈' : 'Home') : platforms[key].title);
  });
  try { localStorage.setItem('mouse-sanctuary-language', language); } catch {}
  if (session) {
    window.NPLabSession = {...session, language};
    byId('platform-frame').contentWindow?.postMessage({type: 'nplab-language', language}, location.origin);
  }
}

async function saveLanguage(next) {
  const sequence = ++saveSequence;
  const previous = language;
  language = next;
  applyLanguage();
  if (!session) return;
  byId('language-select').disabled = true;
  try {
    await api('/hub/preferences', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': session.user.csrf}, body: JSON.stringify({language})});
    try { localStorage.setItem(`nplab-language-${session.user.id}`, language); } catch {}
    byId('language-status').textContent = '';
  } catch (error) {
    if (sequence === saveSequence) { language = previous; applyLanguage(); }
    byId('language-status').textContent = language === 'ko' ? '언어 설정 저장 실패' : 'Could not save language';
    if (error.status === 401) endSession();
  } finally { byId('language-select').disabled = false; }
}

function endSession() {
  byId('auth-language-slot').append(byId('language-control'));
  document.title = 'NPLab Portal';
  if (byId('unavailable').open) byId('unavailable').close();
  session = undefined;
  window.NPLabSession = undefined;
  byId('platform-frame').removeAttribute('src');
  byId('workspace').hidden = true;
  byId('auth').hidden = false;
  byId('password').value = '';
}

function showPlatform(name, account = false) {
  if (!session) return;
  byId('native-nav').replaceChildren();
  byId('native-nav').hidden = true;
  currentPlatform = Object.hasOwn(platforms, name) ? name : 'home';
  const platform = platforms[currentPlatform];
  byId('platform-title').textContent = platform.title;
  document.title = platform.title;
  byId('platform-menu').open = false;
  byId('platform-icon').hidden = !platform.icon;
  if (platform.icon) byId('platform-icon').src = platform.icon;
  document.querySelectorAll('#platform-nav [data-platform]').forEach(link => {
    if (link.dataset.platform === currentPlatform) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  byId('home').hidden = currentPlatform !== 'home';
  const frame = byId('platform-frame');
  frame.hidden = currentPlatform === 'home';
  if (platform.path) frame.src = platform.path + (account ? '?portalAccount=1' : '');
  else frame.removeAttribute('src');
}

function showUnavailable(name) {
  byId('platform-menu').open = false;
  byId('unavailable-platform').textContent = platforms[name].title;
  if (!byId('unavailable').open) byId('unavailable').showModal();
}

function route() {
  const query = new URLSearchParams(location.search);
  const name = query.get('platform');
  if (name === 'omics' || name === 'singlecell') {
    history.replaceState(null, '', '/');
    showPlatform('home');
    showUnavailable(name);
    return;
  }
  showPlatform(name || 'home', query.get('account') === '1');
}

async function loadSession(afterLogin = false) {
  try {
    session = await api('/hub/session');
    if (previousUserId !== undefined && previousUserId !== session.user.id) {
      byId('platform-frame').removeAttribute('src');
    }
    previousUserId = session.user.id;
    if (afterLogin && !session.saved) await saveLanguage(language);
    else language = session.language;
    byId('account').textContent = session.user.username;
    byId('menu-language-slot').append(byId('language-control'));
    byId('auth').hidden = true;
    byId('workspace').hidden = false;
    applyLanguage();
    route();
  } catch (error) {
    endSession();
    if (error.status !== 401) {
      byId('auth-error').textContent = language === 'ko' ? '계정 서버에 연결할 수 없습니다. 잠시 후 다시 시도하세요.' : 'Account service unavailable. Please try again.';
    }
  } finally { byId('session-loading').hidden = true; }
}

byId('login').addEventListener('submit', async event => {
  event.preventDefault();
  byId('login-button').disabled = true;
  byId('auth-error').textContent = '';
  try {
    await api('/api/login', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({username: byId('username').value, password: byId('password').value})});
    byId('password').value = '';
    history.replaceState(null, '', '/');
    await loadSession(true);
  } catch (error) {
    byId('auth-error').textContent = language === 'ko' ? '로그인하지 못했습니다. 계정 정보와 서버 연결을 확인하세요.' : error.message;
  } finally { byId('login-button').disabled = false; }
});

document.querySelectorAll('[data-platform]').forEach(link => link.addEventListener('click', event => {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  if (['omics','singlecell'].includes(link.dataset.platform)) {
    showUnavailable(link.dataset.platform);
    return;
  }
  history.pushState(null, '', link.href);
  route();
}));
window.addEventListener('popstate', route);
document.addEventListener('click', event => {
  if (!byId('platform-menu').contains(event.target)) byId('platform-menu').open = false;
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && byId('platform-menu').open) {
    byId('platform-menu').open = false;
    byId('platform-menu').querySelector('summary').focus();
  }
});
byId('language-select').addEventListener('change', event => saveLanguage(event.target.value));
byId('logout').addEventListener('click', async () => {
  try {
    await api('/api/logout', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': session.user.csrf}, body: '{}'});
    try { localStorage.setItem('nplab-session-ended', String(Date.now())); } catch {}
    endSession();
  } catch { byId('portal-error').hidden = false; byId('portal-error').textContent = 'Could not sign out. Please try again.'; }
});
byId('my-account').addEventListener('click', () => {
  history.pushState(null, '', '/?platform=mouse&account=1');
  route();
});
byId('refresh').addEventListener('click', () => loadSession());
byId('help').addEventListener('click', () => byId('help-dialog').showModal());
window.addEventListener('message', event => {
  if (event.origin !== location.origin || event.source !== byId('platform-frame').contentWindow) return;
  if (event.data?.type === 'nplab-expired') endSession();
  if (event.data?.type === 'nplab-navigation' && event.data.platform === currentPlatform) {
    const nav = byId('native-nav');
    const focusedId = document.activeElement?.dataset.nativeId;
    const items = event.data.items || [];
    nav.replaceChildren(...items.map(item => {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = item.label;
      button.dataset.nativeId = item.id;
      button.disabled = item.disabled;
      button.setAttribute('aria-pressed', String(item.active));
      button.addEventListener('click', () => {
        byId('platform-frame').contentWindow.postMessage({type: 'nplab-select-tool', id: item.id}, location.origin);
      });
      return button;
    }));
    nav.hidden = !items.length;
    if (focusedId !== undefined) [...nav.children].find(button => button.dataset.nativeId === focusedId)?.focus();
  }
});
window.addEventListener('storage', event => {
  if (event.key === 'nplab-session-ended') endSession();
  if (session && event.key === `nplab-language-${session.user.id}` && ['en','ko'].includes(event.newValue)) {
    language = event.newValue;
    applyLanguage();
  }
});
setInterval(async () => {
  if (!session) return;
  try {
    const current = await api('/hub/session');
    if (current.user.id !== session.user.id || current.user.role !== session.user.role) {
      await loadSession();
      return;
    }
    session = current;
    byId('account').textContent = current.user.username;
    if (!byId('language-select').disabled && language !== current.language) { language = current.language; applyLanguage(); }
  } catch (error) { if (error.status === 401) endSession(); }
}, 15000);
new ResizeObserver(entries => {
  document.body.style.setProperty('--portal-header-height', `${entries[0].target.offsetHeight}px`);
}).observe(document.querySelector('.workspace-header'));
applyLanguage();
loadSession();

byId('native-nav').addEventListener('keydown', event => {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
  const buttons = [...byId('native-nav').querySelectorAll('button:not(:disabled)')];
  const index = buttons.indexOf(document.activeElement);
  if (index < 0) return;
  event.preventDefault();
  let next = index;
  if (event.key === 'Home') next = 0;
  if (event.key === 'End') next = buttons.length - 1;
  if (event.key === 'ArrowLeft') next = (index + buttons.length - 1) % buttons.length;
  if (event.key === 'ArrowRight') next = (index + 1) % buttons.length;
  buttons[next].focus();
  buttons[next].click();
});
