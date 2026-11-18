// Homepage "Is my college + major covered?" lookup. Reads the same data as /coverage and the tools.
(function () {
  var sel = document.getElementById('covCollege');
  var inp = document.getElementById('covMajor');
  var out = document.getElementById('covOut');
  if (!sel || !inp || !out) { return; }
  var cov = null;

  function t(key, vars) {
    return window.UCPLAN_I18N ? window.UCPLAN_I18N.t(key, vars) : key;
  }
  function yr(y) { return String(y).replace('-', '\u2013'); }
  function el(tag, text, cls) {
    var e = document.createElement(tag);
    if (text) { e.textContent = text; }
    if (cls) { e.className = cls; }
    return e;
  }

  function fillColleges() {
    var keep = sel.value;
    while (sel.options.length > 1) { sel.remove(1); }
    cov.colleges.forEach(function (name, i) {
      var o = document.createElement('option');
      o.value = String(i);
      o.textContent = name;
      sel.appendChild(o);
    });
    sel.value = keep;
  }

  function yearsFor(major, idx) {
    var ys = [];
    Object.keys(major.years).forEach(function (y) {
      if (major.years[y].indexOf(idx) !== -1) { ys.push(yr(y)); }
    });
    return ys;
  }

  function render() {
    out.textContent = '';
    if (!cov) { return; }
    if (sel.value === '') {
      out.appendChild(el('p', t('index.cov.pick'), 'hint'));
      return;
    }
    var idx = parseInt(sel.value, 10);
    var q = inp.value.trim().toLowerCase();
    var perUc = cov.ucs.map(function (u) {
      var have = u.majors.filter(function (m) { return yearsFor(m, idx).length > 0; });
      return { uc: u, have: have };
    });
    if (!q) {
      var total = 0, campuses = 0;
      perUc.forEach(function (p) { total += p.have.length; if (p.have.length) { campuses++; } });
      out.appendChild(el('p', t('index.cov.summary', { college: cov.colleges[idx], n: total, u: campuses }), 'cov-summary'));
      var ul = el('ul', '', 'cov-list');
      perUc.forEach(function (p) {
        var yrs = {};
        p.have.forEach(function (m) { yearsFor(m, idx).forEach(function (y) { yrs[y] = true; }); });
        var li = el('li');
        li.appendChild(el('strong', p.uc.name));
        li.appendChild(document.createTextNode(' \u2014 ' + t('index.cov.count', { n: p.have.length }) + (p.have.length ? ' (' + Object.keys(yrs).join(', ') + ')' : '')));
        ul.appendChild(li);
      });
      out.appendChild(ul);
      return;
    }
    var found = 0;
    perUc.forEach(function (p) {
      var hits = p.uc.majors.filter(function (m) { return m.name.toLowerCase().indexOf(q) !== -1; });
      if (!hits.length) { return; }
      found += hits.length;
      out.appendChild(el('h4', p.uc.name));
      var ul = el('ul', '', 'cov-list');
      hits.forEach(function (m) {
        var ys = yearsFor(m, idx);
        var li = el('li');
        li.appendChild(document.createTextNode(m.name + ' \u2014 '));
        li.appendChild(el('span', ys.length ? t('index.cov.yes', { years: ys.join(', ') }) : t('index.cov.no'), ys.length ? 'cov-yes' : 'cov-no'));
        ul.appendChild(li);
      });
      out.appendChild(ul);
    });
    if (!found) { out.appendChild(el('p', t('index.cov.none', { q: inp.value.trim() }), 'hint')); }
  }

  function start() {
    cov = window.UCPLAN_COVERAGE;
    if (!cov) { return; }
    fillColleges();
    render();
  }

  sel.addEventListener('change', render);
  inp.addEventListener('input', render);
  // i18n.js loads coverage.json first, then fires this after the text is applied
  document.addEventListener('ucplan:lang', function () {
    if (cov) { render(); } else { start(); }
  });
  if (window.UCPLAN_COVERAGE) { start(); }
})();
