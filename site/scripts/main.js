/* ============================================================================
   CybNodes : landing : animations légères et accessibles.
   1) révélation au scroll  2) copier le code  3) réseau de nœuds (hero)
   ============================================================================ */
(function () {
  "use strict";
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- 1. Révélation au scroll ---- */
  var reveals = document.querySelectorAll(".reveal");
  if (reduce || !("IntersectionObserver" in window)) {
    reveals.forEach(function (el) { el.classList.add("is-in"); });
  } else {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); }
      });
    }, { threshold: 0.14 });
    reveals.forEach(function (el) { io.observe(el); });
  }

  /* ---- 2. Copier le code ---- */
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var code = btn.closest(".code").querySelector("pre").innerText;
      navigator.clipboard.writeText(code).then(function () {
        var old = btn.textContent;
        btn.textContent = "copié ✓";
        setTimeout(function () { btn.textContent = old; }, 1400);
      }).catch(function () {});
    });
  });

  /* ---- 3. Réseau de nœuds animé (hero) ---- */
  var canvas = document.getElementById("net-canvas");
  if (!canvas || reduce) return;
  var ctx = canvas.getContext("2d");
  var nodes = [];
  var DPR = Math.min(window.devicePixelRatio || 1, 2);
  var W = 0, H = 0;

  function resize() {
    var r = canvas.getBoundingClientRect();
    W = r.width; H = r.height;
    canvas.width = W * DPR; canvas.height = H * DPR;
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    var count = Math.max(22, Math.min(46, Math.round(W / 26)));
    nodes = [];
    for (var i = 0; i < count; i++) {
      nodes.push({
        x: Math.random() * W, y: Math.random() * H,
        vx: (Math.random() - 0.5) * 0.28, vy: (Math.random() - 0.5) * 0.28,
        r: Math.random() * 1.6 + 0.8
      });
    }
  }

  function frame() {
    ctx.clearRect(0, 0, W, H);
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      n.x += n.vx; n.y += n.vy;
      if (n.x < 0 || n.x > W) n.vx *= -1;
      if (n.y < 0 || n.y > H) n.vy *= -1;
      for (var j = i + 1; j < nodes.length; j++) {
        var m = nodes[j], dx = n.x - m.x, dy = n.y - m.y;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < 128) {
          ctx.strokeStyle = "rgba(0, 229, 255," + (0.14 * (1 - d / 128)) + ")";
          ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(n.x, n.y); ctx.lineTo(m.x, m.y); ctx.stroke();
        }
      }
      ctx.fillStyle = "rgba(122, 240, 255, 0.7)";
      ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2); ctx.fill();
    }
    requestAnimationFrame(frame);
  }

  resize();
  window.addEventListener("resize", resize);
  requestAnimationFrame(frame);
})();
