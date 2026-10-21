/* واجهة الموقع: القائمة، البحث والتصفية، النموذج، والخلفية الشبكية المتحركة */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };

  /* قائمة الهاتف */
  var tg = $('.nav-toggle'), nav = $('#nav');
  if (tg && nav) {
    tg.addEventListener('click', function () {
      var o = nav.classList.toggle('open');
      tg.setAttribute('aria-expanded', o); tg.setAttribute('aria-label', o ? 'إغلاق القائمة' : 'فتح القائمة');
    });
    nav.addEventListener('click', function (e) { if (e.target.tagName === 'A') { nav.classList.remove('open'); tg.setAttribute('aria-expanded', 'false'); } });
  }

  /* بحث وتصفية المشاريع */
  var q = $('#q'), cards = [].slice.call(document.querySelectorAll('.proj')), cnt = $('#count'), none = $('#noResults');
  if (q && cards.length) {
    var cat = 'all';
    var norm = function (s) { return (s || '').toLowerCase().replace(/[\u064B-\u065F\u0640]/g, '').replace(/[أإآ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه'); };
    var run = function () {
      var t = norm(q.value.trim()), n = 0;
      cards.forEach(function (c) {
        var ok = (cat === 'all' || c.dataset.cat === cat) && (!t || norm(c.dataset.s).indexOf(t) > -1);
        c.hidden = !ok; if (ok) n++;
      });
      if (cnt) cnt.textContent = n + ' مشروعاً';
      if (none) none.hidden = n > 0;
    };
    q.addEventListener('input', run);
    [].forEach.call(document.querySelectorAll('.chip'), function (b) {
      b.addEventListener('click', function () {
        cat = b.dataset.f;
        [].forEach.call(document.querySelectorAll('.chip'), function (x) { x.setAttribute('aria-pressed', x === b); });
        run();
      });
    });
  }

  /* نموذج التواصل: يفتح تطبيق البريد برسالة جاهزة */
  var f = $('#mailForm');
  if (f) f.addEventListener('submit', function (e) {
    e.preventDefault();
    var body = 'الاسم: ' + $('#f-name').value + '\n\n' + $('#f-msg').value;
    location.href = 'mailto:' + f.dataset.email + '?subject=' + encodeURIComponent($('#f-sub').value) + '&body=' + encodeURIComponent(body);
  });

  /* ===== الخلفية الشبكية =====
     إصلاح عدم الحركة على الكمبيوتر: النسخة القديمة كانت توقف الحركة كلياً عندما يكون إعداد
     "تقليل الحركة" مفعّلاً في النظام (شائع في ويندوز). هنا تبقى الحركة هادئة وبطيئة في هذه الحالة،
     ويستطيع الزائر إيقافها بزر الخلفية، ويُحفظ اختياره. */
  var cv = $('#bgNet'); if (!cv || !cv.getContext) return;
  var ctx = cv.getContext('2d'), btn = $('#bgToggle');
  var reduce = matchMedia('(prefers-reduced-motion: reduce)').matches, coarse = matchMedia('(pointer: coarse)').matches;
  var PAL = [[88, 134, 255], [116, 138, 232], [114, 198, 84], [246, 174, 30]];
  var W = 0, H = 0, dpr = 1, nodes = [], raf = 0, last = 0, paused = false, ptr = { x: -9999, y: -9999, on: false };
  try { paused = localStorage.getItem('bgPaused') === '1'; } catch (e) {}
  var speed = reduce ? 0.3 : 1;

  function build() {
    var n = Math.round(Math.min(95, Math.max(28, W * H / 16000)) * (coarse ? 0.65 : 1));
    nodes = [];
    for (var i = 0; i < n; i++) {
      var d = [0.4, 0.7, 1][i % 3], c = PAL[(Math.random() * (i % 7 === 0 ? 4 : 2)) | 0];
      nodes.push({ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - .5) * 26 * d, vy: (Math.random() - .5) * 26 * d,
        r: .9 + d * 1.6 + Math.random(), d: d, c: c, ph: Math.random() * 6.28, px: 0, py: 0, h: 0 });
    }
  }
  function size() {
    var w = innerWidth, h = innerHeight;
    if (nodes.length && w === W && Math.abs(h - H) < 120) return;
    W = w; H = h; dpr = Math.min(2, devicePixelRatio || 1);
    cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); build();
  }
  function draw(ts, dt) {
    ctx.clearRect(0, 0, W, H);
    var sy = scrollY, i, j, a, b, dx, dy, d2, t, LINK = 140, R = 170;
    for (i = 0; i < nodes.length; i++) {
      a = nodes[i];
      a.x += a.vx * dt * speed; a.y += a.vy * dt * speed;
      if (a.x < -20) a.x = W + 20; else if (a.x > W + 20) a.x = -20;
      if (a.y < -20) a.y = H + 20; else if (a.y > H + 20) a.y = -20;
      a.px = a.x; a.py = (((a.y - sy * a.d * .12) % H) + H) % H;
      var tgt = 0;
      if (ptr.on) { dx = ptr.x - a.px; dy = ptr.y - a.py; var d = Math.sqrt(dx * dx + dy * dy) || 1; if (d < R) { tgt = 1 - d / R; a.x += dx / d * tgt * 60 * dt; a.y += dy / d * tgt * 60 * dt; } }
      a.h += (tgt - a.h) * Math.min(1, dt * 8);
    }
    ctx.lineWidth = 1;
    for (i = 0; i < nodes.length; i++) {
      a = nodes[i];
      for (j = i + 1; j < nodes.length; j++) {
        b = nodes[j]; if (a.d !== b.d) continue;
        dx = a.px - b.px; dy = a.py - b.py; d2 = dx * dx + dy * dy;
        if (d2 > LINK * LINK) continue;
        t = 1 - Math.sqrt(d2) / LINK;
        ctx.strokeStyle = 'rgba(' + ((a.c[0] + b.c[0]) >> 1) + ',' + ((a.c[1] + b.c[1]) >> 1) + ',' + ((a.c[2] + b.c[2]) >> 1) + ',' + (t * .42 * a.d * (1 + (a.h + b.h) * .8)) + ')';
        ctx.beginPath(); ctx.moveTo(a.px, a.py); ctx.lineTo(b.px, b.py); ctx.stroke();
      }
    }
    if (ptr.on) {
      for (i = 0; i < nodes.length; i++) { a = nodes[i]; if (a.h > .05) { ctx.strokeStyle = 'rgba(114,198,84,' + (a.h * .5) + ')'; ctx.beginPath(); ctx.moveTo(ptr.x, ptr.y); ctx.lineTo(a.px, a.py); ctx.stroke(); } }
    }
    for (i = 0; i < nodes.length; i++) {
      a = nodes[i]; var tw = .75 + .25 * Math.sin(ts / 1000 * 1.2 + a.ph), r = a.r * (1 + a.h * .8);
      ctx.fillStyle = 'rgba(' + a.c[0] + ',' + a.c[1] + ',' + a.c[2] + ',' + Math.min(1, (.35 + a.d * .55) * tw + a.h * .3) + ')';
      ctx.beginPath(); ctx.arc(a.px, a.py, r, 0, 6.283); ctx.fill();
    }
  }
  function frame(ts) {
    raf = 0; if (paused) return;
    var dt = Math.min(.05, (ts - last) / 1000 || .016); last = ts;
    if (!document.hidden) draw(ts, dt);
    raf = requestAnimationFrame(frame);
  }
  function setPaused(p, save) {
    paused = p;
    if (btn) { btn.setAttribute('aria-pressed', p); var l = p ? 'تشغيل حركة الخلفية' : 'إيقاف حركة الخلفية'; btn.setAttribute('aria-label', l); btn.title = l; }
    if (save) { try { localStorage.setItem('bgPaused', p ? '1' : '0'); } catch (e) {} }
    if (p) { if (raf) cancelAnimationFrame(raf); raf = 0; draw(performance.now(), 0); }
    else if (!raf) { last = performance.now(); raf = requestAnimationFrame(frame); }
  }
  size(); setPaused(paused, false);
  var rt; addEventListener('resize', function () { clearTimeout(rt); rt = setTimeout(function () { size(); if (paused) draw(performance.now(), 0); }, 120); });
  addEventListener('pointermove', function (e) { ptr.x = e.clientX; ptr.y = e.clientY; ptr.on = true; }, { passive: true });
  addEventListener('pointerleave', function () { ptr.on = false; });
  addEventListener('touchend', function () { ptr.on = false; }, { passive: true });
  document.addEventListener('visibilitychange', function () { if (!document.hidden && !paused && !raf) { last = performance.now(); raf = requestAnimationFrame(frame); } });
  if (btn) btn.addEventListener('click', function () { setPaused(!paused, true); });
})();
