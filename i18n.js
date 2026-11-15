(function () {
  var LANGS = [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Español' },
    { code: 'zh-CN', name: '简体中文' },
    { code: 'zh-TW', name: '繁體中文' },
    { code: 'ko', name: '한국어' },
    { code: 'ja', name: 'にほんご' }
  ];
  var KEY = 'ucplan.lang';
  var cache = {};

  // First visit: follow the browser language, English when there is no match.
  // A saved choice (the language button) always wins.
  function detect() {
    var list = (navigator.languages && navigator.languages.length) ? navigator.languages : [navigator.language || 'en'];
    for (var i = 0; i < list.length; i++) {
      var l = String(list[i] || '').toLowerCase();
      if (l.indexOf('zh') === 0) { return (/hant|-tw|-hk|-mo/.test(l)) ? 'zh-TW' : 'zh-CN'; }
      if (l.indexOf('es') === 0) { return 'es'; }
      if (l.indexOf('ko') === 0) { return 'ko'; }
      if (l.indexOf('ja') === 0) { return 'ja'; }
      if (l.indexOf('en') === 0) { return 'en'; }
    }
    return 'en';
  }

  function langName(code) {
    for (var i = 0; i < LANGS.length; i++) {
      if (LANGS[i].code === code) { return LANGS[i].name; }
    }
    return 'English';
  }

  function isKnown(code) {
    for (var i = 0; i < LANGS.length; i++) {
      if (LANGS[i].code === code) { return true; }
    }
    return false;
  }

  function apply(dict) {
    var els = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < els.length; i++) {
      var v = dict[els[i].getAttribute('data-i18n')];
      if (typeof v === 'string') { els[i].textContent = v; }
    }
    var page = document.documentElement.getAttribute('data-page');
    if (page) {
      if (dict[page + '.meta.title']) { document.title = dict[page + '.meta.title']; }
      var m = document.querySelector('meta[name="description"]');
      if (m && dict[page + '.meta.desc']) { m.setAttribute('content', dict[page + '.meta.desc']); }
    }
  }

  function load(code, done) {
    if (cache[code]) { done(cache[code]); return; }
    fetch('lang/' + code + '.json').then(function (r) { return r.json(); }).then(function (d) {
      cache[code] = d;
      done(d);
    }).catch(function () { /* keep current language on failure */ });
  }

  function setLang(code, remember) {
    if (!isKnown(code)) { code = 'en'; }
    if (remember !== false) {
      try { localStorage.setItem(KEY, code); } catch (e) { /* private mode */ }
    }
    document.documentElement.setAttribute('lang', code);
    var btn = document.getElementById('langBtn');
    if (btn) { btn.textContent = langName(code); }
    closeList();
    if (code === 'en') {
      load('en', apply);
    } else {
      load(code, apply);
    }
  }

  function closeList() {
    var list = document.getElementById('langList');
    var btn = document.getElementById('langBtn');
    if (list) { list.hidden = true; }
    if (btn) { btn.setAttribute('aria-expanded', 'false'); }
  }

  function openList() {
    var list = document.getElementById('langList');
    var btn = document.getElementById('langBtn');
    if (list) { list.hidden = false; }
    if (btn) { btn.setAttribute('aria-expanded', 'true'); }
  }

  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('langBtn');
    var list = document.getElementById('langList');
    if (btn && list) {
      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        if (list.hidden) { openList(); } else { closeList(); }
      });
      var items = list.querySelectorAll('[data-lang]');
      for (var i = 0; i < items.length; i++) {
        items[i].addEventListener('click', function (e) {
          setLang(e.target.getAttribute('data-lang'));
        });
      }
      document.addEventListener('click', function (e) {
        if (!list.hidden && !list.contains(e.target) && e.target !== btn) { closeList(); }
      });
      document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { closeList(); }
      });
    }
    var stored = null;
    try { stored = localStorage.getItem(KEY); } catch (e) { stored = null; }
    var saved = !!(stored && isKnown(stored));
    // pages with no translated text (static SEO pages) stay English
    var start = saved ? stored : (document.querySelector('[data-i18n^="index."],[data-i18n^="tos."],[data-i18n^="cuc."]') ? detect() : 'en');
    if (btn) { btn.textContent = langName(start); }
    if (start !== 'en') { setLang(start, saved); }
  });
})();
