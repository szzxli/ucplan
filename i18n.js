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
  var stats = null;      // numbers read from coverage.json + ucc-majors.json (the same data the tools use)
  var current = 'en';
  var statsReq = null;

  // First visit: follow the browser language, English when we have no match. A saved choice always wins.
  function detect() {
    var list = (navigator.languages && navigator.languages.length) ? navigator.languages : [navigator.language || 'en'];
    for (var i = 0; i < list.length; i++) {
      var l = String(list[i] || '').toLowerCase();
      if (l.indexOf('zh') === 0) {
        return (/hant|-tw|-hk|-mo/.test(l)) ? 'zh-TW' : 'zh-CN';
      }
      if (l.indexOf('es') === 0) { return 'es'; }
      if (l.indexOf('ko') === 0) { return 'ko'; }
      if (l.indexOf('ja') === 0) { return 'ja'; }
      if (l.indexOf('en') === 0) { return 'en'; }
    }
    return 'en';
  }

  function loadStats() {
    if (statsReq) { return statsReq; }
    statsReq = Promise.all([
      fetch('/coverage.json').then(function (r) { return r.json(); }),
      fetch('/ucc-majors.json').then(function (r) { return r.json(); })
    ]).then(function (res) {
      var cov = res[0], ucc = res[1];
      stats = {
        colleges: cov.counts.colleges, ucs: cov.counts.ucs, majors: cov.counts.uc_majors,
        ucmajors: ucc.count, uccampuses: ucc.campuses.length, assistdate: cov.assist_pulled
      };
      window.UCPLAN_COVERAGE = cov;
      return stats;
    }).catch(function () { stats = null; return null; });
    return statsReq;
  }

  function fmtDate(iso, code) {
    try {
      var d = new Date(iso + 'T00:00:00Z');
      return d.toLocaleDateString(code, { year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC' });
    } catch (e) { return iso; }
  }

  function fill(str, vars) {
    return str.replace(/\{([a-z]+)\}/g, function (m, k) {
      return (vars && vars[k] !== undefined) ? String(vars[k]) : m;
    });
  }

  function statVars(code) {
    if (!stats) { return null; }
    var v = {};
    for (var k in stats) { if (Object.prototype.hasOwnProperty.call(stats, k)) { v[k] = stats[k]; } }
    v.assistdate = fmtDate(stats.assistdate, code);
    return v;
  }

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

  // t('key', {vars}) for scripts (coverage.js) that build text at runtime.
  window.UCPLAN_I18N = {
    t: function (key, vars) {
      var d = cache[current] || cache.en || {};
      var v = d[key];
      if (typeof v !== 'string') { v = (cache.en || {})[key] || key; }
      return fill(v, vars);
    },
    lang: function () { return current; }
  };

  function apply(dict, code) {
    var sv = statVars(code);
    var els = document.querySelectorAll('[data-i18n]');
    for (var i = 0; i < els.length; i++) {
      var v = dict[els[i].getAttribute('data-i18n')];
      if (typeof v !== 'string') { continue; }
      if (/\{[a-z]+\}/.test(v)) {
        v = fill(v, sv);
        // numbers not available (offline or fetch failed): keep the static English text already on the page
        if (/\{(colleges|ucs|majors|ucmajors|uccampuses|assistdate)\}/.test(v)) { continue; }
      }
      els[i].textContent = v;
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
    Promise.all([
      fetch('/lang/' + code + '.json').then(function (r) { return r.json(); }),
      cache.en ? Promise.resolve(cache.en) : fetch('/lang/en.json').then(function (r) { return r.json(); }),
      loadStats()
    ]).then(function (res) {
      cache[code] = res[0];
      if (!cache.en) { cache.en = res[1]; }
      done(res[0]);
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
    current = code;
    load(code, function (d) {
      apply(d, code);
      document.dispatchEvent(new CustomEvent('ucplan:lang', { detail: { lang: code } }));
    });
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
          setLang(e.target.getAttribute('data-lang'), true);
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
    var page = document.documentElement.getAttribute('data-page');
    // Homepage defaults to English. A saved choice still wins.
    // Other translated pages follow the browser language. Static SEO pages stay English.
    var followBrowser = page !== 'index' && document.querySelector('[data-i18n^="index."],[data-i18n^="tos."],[data-i18n^="cuc."],[data-i18n^="cov."],[data-i18n^="tna."],[data-i18n^="cns."]');
    var start = saved ? stored : (followBrowser ? detect() : 'en');
    if (btn) { btn.textContent = langName(start); }
    // English also loads the dictionary so tokens and runtime text are ready.
    setLang(start, saved);
  });
})();
