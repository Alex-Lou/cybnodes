/* ============================================================================
   CybNodes : bilingue FR/EN. Le francais est la source (inline dans le HTML).
   Ici vit la traduction anglaise + la bascule. Le bouton #langToggle alterne.
   ============================================================================ */
(function () {
  "use strict";

  var EN = {
    "nav.what": `What`,
    "nav.install": `Install`,
    "nav.networks": `Networks`,
    "hero.tag": `neural circuit / model-agnostic`,
    "hero.lead": `Don't grow the brain by brute force. Surround it with <strong>structured, verifiable circuits</strong>, and say every result back in your model's voice.`,
    "hero.cta1": `Install →`,
    "hero.cta2": `See the code`,
    "quoi.eyebrow": `// what it is`,
    "quoi.h2": `A <span class="grad">Python library</span>, not a black box`,
    "quoi.lead": `<code>pip install cybnodes</code>, then <code>import cybnodes</code>. Not an app, not a service to host: a piece you plug <strong>around your own model</strong>. An LLM is great at talking, bad at guaranteeing. CybNodes puts networks in front of it that answer exactly and verifiably.`,
    "card.lib.h": `Library`,
    "card.lib.p": `Pure Python, zero required dependency. You import it and compose.`,
    "card.agn.h": `Model-agnostic`,
    "card.agn.p": `You bring your LLM (ollama, API, local…). CybNodes brings the circuits.`,
    "card.ver.h": `Verifiable`,
    "card.ver.p": `Every network returns a traceable answer: exact math, graph node, web source.`,
    "why.eyebrow": `// why`,
    "why.h2": `Knowledge lives <span class="grad">outside</span> the model`,
    "why.lead": `Fixing a fact no longer means retraining: you edit a file.`,
    "why.th1": `Without CybNodes`,
    "why.th2": `With CybNodes`,
    "why.r1a": `"47 × 38 ?" → the LLM guesses, sometimes wrong`,
    "why.r1b": `exact math (safe AST), always right`,
    "why.r2a": `"what is X ?" → the LLM hallucinates`,
    "why.r2b": `answer from your knowledge graph`,
    "why.r3a": `"what's new about Y ?" → stale data`,
    "why.r3b": `web search, with the source cited`,
    "why.r4a": `fix a fact → retrain`,
    "why.r4b": `edit a file, zero training`,
    "why.r5a": `network unsure → confident wrong answer`,
    "why.r5b": `it goes quiet below the threshold, the model takes over (tunable threshold)`,
    "inst.eyebrow": `// 60 seconds`,
    "inst.h2": `Install & <span class="grad">start</span>`,
    "copy": `copy`,
    "code.t1": `# or from source:`,
    "code.q1": `# 1. You bring YOUR model, any callable`,
    "code.q2": `# 2. You surround it with networks`,
    "code.q3": `# 3. You ask`,
    "code.q4": `# -> exact, never wrong`,
    "code.q5": `# -> from your graph, Aria's voice`,
    "code.q6": `# -> no network -> your model answers`,
    "arch.eyebrow": `// architecture`,
    "arch.h2": `The <span class="grad">5 layers</span>`,
    "arch.l1t": `The Conductor`,
    "arch.l1s": `your model, its voice, its personality`,
    "arch.l2t": `The Router`,
    "arch.l2s": `tries the networks; it keeps an answer only when the network is sure (tunable threshold), otherwise it passes control on. One that crashes breaks nothing.`,
    "arch.l3t": `The Networks`,
    "arch.l3s": `one capability each, independent (math, knowledge, web…)`,
    "arch.l4t": `The Weaver`,
    "arch.l4s": `says the raw result back in the conductor's voice`,
    "arch.l5t": `The Memory`,
    "arch.l5s": `captures sure facts about the user, pluggable backend`,
    "flow.q": `the question`,
    "flow.router": `ROUTER`,
    "flow.calc": `Math`,
    "flow.know": `Knowledge`,
    "flow.web": `Web`,
    "flow.weaver": `WEAVER`,
    "flow.voice": `voice`,
    "flow.answer": `the answer`,
    "flow.cap": `The question comes in, the <strong>router</strong> queries the networks, one answers — or none. The <strong>weaver</strong> says it back in the model's voice, and the answer comes out, verifiable.`,
    "net.eyebrow": `// networks included`,
    "net.h2": `The <span class="grad">circuits</span>, ready to plug in`,
    "net.lead": `Shared rule: a network stays quiet the moment it doubts. Deterministic networks (math) hand control back outright; fuzzy networks (knowledge, web) score their confidence, and the router drops them below the threshold. The upshot: the answer is never shaky, the model takes over when in doubt.`,
    "net.calc.h": `Exact math`,
    "net.calc.p": `Safe arithmetic via AST (zero <code>eval</code>). Symbols and words ("times", "power"…). The LLM never gets a calculation wrong again.`,
    "net.know.h": `Knowledge (GraphRAG)`,
    "net.know.p": `Answers from a graph of <code>subject-relation-object</code> triples. You fix a fact by editing the graph, no retraining.`,
    "net.web.h": `Web search`,
    "net.web.p": `Fresh info via the Brave Search API, with the source cited. Honest: "I searched, and…". Stays quiet cleanly without a key.`,
    "net.recall.h": `Recall that recites`,
    "net.recall.p": `Recites an already validated answer (never rephrased, so zero hallucination), tolerates typos, and calibrates its own abstention threshold (0.7.0): "not exceeding a given error rate" becomes a measurable guarantee, not a hope.`,
    "net.ground.h": `Grounding before serving`,
    "net.ground.p": `Wraps a network and checks grounding before answering: if nearby golds contradict, it abstains. It only removes the doubtful, invents nothing, fail-safe.`,
    "ext.eyebrow": `// extensible`,
    "ext.h2": `Write <span class="grad">your network</span> in 6 lines`,
    "ext.lead": `Subclass <code>Network</code>, return a <code>Result</code> when you know, otherwise <code>None</code>, and control passes on.`,
    "code.m1": `# not my job -> I pass control back`,
    "code.m2": `# a VERIFIABLE result`,
    "code.m3": `# plugged in. That's it.`,
    "when.use.h": `Use it when…`,
    "when.use.p": `you want an LLM to answer <strong>exactly, verifiably or up to date</strong> on certain topics, while keeping its voice, without retraining.`,
    "when.no.h": `No need when…`,
    "when.no.p": `it's pure free generation (writing, brainstorming). There, your model alone is enough, CybNodes simply lets it lead.`,
    "footer.docs": `Documentation`,
    "footer.sign": `Built by CybWu, born around a small AI, made to surround any model. 🐺`,
  };

  var TITLES = {
    fr: "CybNodes : entoure ton LLM de circuits vérifiables",
    en: "CybNodes: surround your LLM with verifiable circuits",
  };
  var KEY = "cyb_lang";
  var els = document.querySelectorAll("[data-i18n]");
  var FR = {};                                  // source francaise capturee depuis le DOM
  els.forEach(function (el) { FR[el.getAttribute("data-i18n")] = el.innerHTML; });

  function apply(lang) {
    els.forEach(function (el) {
      var k = el.getAttribute("data-i18n");
      var v = lang === "en" ? EN[k] : FR[k];
      if (v != null) el.innerHTML = v;
    });
    document.documentElement.lang = lang;
    document.title = TITLES[lang] || TITLES.fr;
    var btn = document.getElementById("langToggle");
    if (btn) btn.textContent = lang === "en" ? "FR" : "EN";
    try { localStorage.setItem(KEY, lang); } catch (e) {}
  }

  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  var initial = saved || ((navigator.language || "").slice(0, 2).toLowerCase() === "en" ? "en" : "fr");
  apply(initial);

  var toggle = document.getElementById("langToggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      apply(document.documentElement.lang === "en" ? "fr" : "en");
    });
  }
})();
