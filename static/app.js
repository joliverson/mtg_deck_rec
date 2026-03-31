(() => {
  "use strict";

  // ── DOM references ──
  const form = document.getElementById("analyze-form");
  const deckInput = document.getElementById("deck-url");
  const analyzeBtn = document.getElementById("analyze-btn");
  const loadingEl = document.getElementById("loading");
  const errorEl = document.getElementById("error");
  const errorMsg = document.getElementById("error-message");
  const resultsEl = document.getElementById("results");

  const commanderImg = document.getElementById("commander-img");
  const deckNameEl = document.getElementById("deck-name");
  const deckStatsEl = document.getElementById("deck-stats");

  const validatedCount = document.getElementById("validated-count");
  const recommendedCount = document.getElementById("recommended-count");
  const cutsCount = document.getElementById("cuts-count");

  const grids = {
    validated: document.getElementById("grid-validated"),
    recommended: document.getElementById("grid-recommended"),
    cuts: document.getElementById("grid-cuts"),
  };

  // Modal
  const modal = document.getElementById("card-modal");
  const modalImg = document.getElementById("modal-img");
  const modalName = document.getElementById("modal-name");
  const modalType = document.getElementById("modal-type");
  const modalSynergy = document.getElementById("modal-synergy");
  const modalInclusion = document.getElementById("modal-inclusion");
  const modalCategory = document.getElementById("modal-category");

  // ── State ──
  let state = { validated: [], recommended_adds: [], potential_cuts: [] };
  let currentDeckUrl = "";

  // AI elements
  const aiBtn = document.getElementById("ai-btn");
  const aiStatus = document.getElementById("ai-status");
  const aiLoading = document.getElementById("ai-loading");
  const aiOutput = document.getElementById("ai-output");
  let llmConfigured = false;

  // Check LLM availability on page load
  fetch("/api/llm-status").then(r => r.json()).then(d => {
    llmConfigured = d.configured;
    if (!llmConfigured) {
      aiStatus.textContent = "Set LLM_API_KEY env var (OpenAI) or LLM_BASE_URL (Ollama) to enable AI recommendations.";
      aiStatus.className = "ai-status info";
      aiStatus.classList.remove("hidden");
    }
  }).catch(() => {});

  // ── Tabs ──
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((tc) => tc.classList.remove("active"));
      tab.classList.add("active");
      document.getElementById("tab-" + tab.dataset.tab).classList.add("active");
    });
  });

  // ── Modal close ──
  document.querySelector(".modal-close").addEventListener("click", closeModal);
  document.querySelector(".modal-backdrop").addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

  function closeModal() {
    modal.classList.add("hidden");
  }

  function openModal(card) {
    modalImg.src = card.image_url;
    modalImg.alt = card.name;
    modalName.textContent = card.name;
    modalType.textContent = card.type_line || "";
    modalSynergy.textContent = card.synergy != null ? (card.synergy >= 0 ? "+" : "") + card.synergy.toFixed(2) : "N/A";
    modalSynergy.className = "stat-value " + synergyClass(card.synergy);
    modalInclusion.textContent = card.inclusion_rate != null ? (card.inclusion_rate * 100).toFixed(1) + "%" : "N/A";
    modalCategory.textContent = card.category || "Not in EDHREC";
    modal.classList.remove("hidden");
  }

  // ── Helpers ──
  function synergyClass(s) {
    if (s == null) return "";
    if (s > 0.1) return "synergy-positive";
    if (s < -0.05) return "synergy-negative";
    return "synergy-neutral";
  }

  function formatSynergy(s) {
    if (s == null) return "N/A";
    return (s >= 0 ? "+" : "") + s.toFixed(2);
  }

  function formatInclusion(r) {
    if (r == null) return "N/A";
    return (r * 100).toFixed(1) + "%";
  }

  // ── Render cards ──
  function renderGrid(container, cards) {
    container.innerHTML = "";
    if (cards.length === 0) {
      container.innerHTML = '<p style="color: var(--text-muted); grid-column: 1/-1;">No cards in this category.</p>';
      return;
    }
    for (const card of cards) {
      const tile = document.createElement("div");
      tile.className = "card-tile";
      tile.addEventListener("click", () => openModal(card));

      const img = document.createElement("img");
      img.src = card.image_url;
      img.alt = card.name;
      img.loading = "lazy";

      const meta = document.createElement("div");
      meta.className = "card-meta";

      const name = document.createElement("div");
      name.className = "card-name";
      name.textContent = card.name;

      const stats = document.createElement("div");
      stats.className = "card-stats";
      const syn = document.createElement("span");
      syn.className = synergyClass(card.synergy);
      syn.textContent = formatSynergy(card.synergy);
      const inc = document.createElement("span");
      inc.textContent = formatInclusion(card.inclusion_rate);
      stats.appendChild(syn);
      stats.appendChild(inc);

      meta.appendChild(name);
      meta.appendChild(stats);
      tile.appendChild(img);
      tile.appendChild(meta);
      container.appendChild(tile);
    }
  }

  // ── Form submit ──
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const deckUrl = deckInput.value.trim();
    if (!deckUrl) return;

    // UI states
    loadingEl.classList.remove("hidden");
    errorEl.classList.add("hidden");
    resultsEl.classList.add("hidden");
    analyzeBtn.disabled = true;

    try {
      const resp = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          deck_url: deckUrl,
          add_threshold: parseFloat(document.getElementById("add-threshold").value),
          cut_threshold: parseFloat(document.getElementById("cut-threshold").value),
        }),
      });

      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error || "Unknown server error");
      }

      // Populate results
      commanderImg.src = data.commander.image_url;
      commanderImg.alt = data.commander.name;
      deckNameEl.textContent = data.deck_name;
      deckStatsEl.textContent = `Commander: ${data.commander.name} · ${data.mainboard_count} mainboard cards · ${data.edhrec_count} EDHREC recommendations`;

      validatedCount.textContent = data.validated.length;
      recommendedCount.textContent = data.recommended_adds.length;
      cutsCount.textContent = data.potential_cuts.length;

      state = data;
      renderGrid(grids.validated, data.validated);
      renderGrid(grids.recommended, data.recommended_adds);
      renderGrid(grids.cuts, data.potential_cuts);

      resultsEl.classList.remove("hidden");

      // Enable AI button if configured
      currentDeckUrl = deckUrl;
      aiBtn.disabled = !llmConfigured;
      aiOutput.classList.add("hidden");
      aiOutput.innerHTML = "";

      // Reset to first tab
      document.querySelectorAll(".tab")[0].click();

    } catch (err) {
      errorMsg.textContent = err.message;
      errorEl.classList.remove("hidden");
    } finally {
      loadingEl.classList.add("hidden");
      analyzeBtn.disabled = false;
    }
  });

  // ── AI Recommendations (streaming) ──
  aiBtn.addEventListener("click", async () => {
    if (!currentDeckUrl || !llmConfigured) return;

    aiBtn.disabled = true;
    aiLoading.classList.remove("hidden");
    aiOutput.classList.add("hidden");
    aiOutput.innerHTML = "";
    aiStatus.classList.add("hidden");

    try {
      const resp = await fetch("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          deck_url: currentDeckUrl,
          add_threshold: parseFloat(document.getElementById("add-threshold").value),
          cut_threshold: parseFloat(document.getElementById("cut-threshold").value),
        }),
      });

      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.error || "Failed to get recommendations");
      }

      aiOutput.classList.remove("hidden");
      aiLoading.classList.add("hidden");

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let rawMarkdown = "";
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;
          const payload = trimmed.slice(6);
          if (payload === "[DONE]") continue;
          try {
            const chunk = JSON.parse(payload);
            if (chunk.error) {
              throw new Error(chunk.error);
            }
            if (chunk.text) {
              rawMarkdown += chunk.text;
              aiOutput.innerHTML = renderMarkdown(rawMarkdown);
              aiOutput.scrollTop = aiOutput.scrollHeight;
            }
          } catch (parseErr) {
            if (parseErr.message && !parseErr.message.includes("JSON")) throw parseErr;
          }
        }
      }
    } catch (err) {
      aiStatus.textContent = err.message;
      aiStatus.className = "ai-status error";
      aiStatus.classList.remove("hidden");
      aiLoading.classList.add("hidden");
    } finally {
      aiBtn.disabled = false;
      aiLoading.classList.add("hidden");
    }
  });

  // ── Card Evaluation Panel ──
  const evalImageInput = document.getElementById("eval-image-input");
  const evalFileInput = document.getElementById("eval-file-input");
  const evalCardList = document.getElementById("eval-card-list");
  const evalBtn = document.getElementById("eval-btn");
  const evalStatus = document.getElementById("eval-status");
  const evalLoading = document.getElementById("eval-loading");
  const evalLoadingText = document.getElementById("eval-loading-text");
  const evalOutput = document.getElementById("eval-output");
  const evalPreview = document.getElementById("eval-image-preview");
  const evalPreviewImg = document.getElementById("eval-preview-img");
  const evalClearImage = document.getElementById("eval-clear-image");
  const evalCardCount = document.getElementById("eval-card-count");

  let pendingImageFile = null;

  function updateEvalBtn() {
    const hasText = evalCardList.value.trim().length > 0;
    const hasImage = pendingImageFile !== null;
    evalBtn.disabled = !(hasText || hasImage) || !currentDeckUrl || !llmConfigured;
    // Update card count
    if (hasText) {
      const lines = evalCardList.value.trim().split("\n").filter(l => l.trim());
      evalCardCount.textContent = `${lines.length} card(s) ready`;
    } else if (hasImage) {
      evalCardCount.textContent = "Image ready — will identify cards first";
    } else {
      evalCardCount.textContent = "";
    }
  }

  evalCardList.addEventListener("input", updateEvalBtn);

  // Image upload
  evalImageInput.addEventListener("change", () => {
    const file = evalImageInput.files[0];
    if (!file) return;
    pendingImageFile = file;
    const url = URL.createObjectURL(file);
    evalPreviewImg.src = url;
    evalPreview.classList.remove("hidden");
    updateEvalBtn();
  });

  evalClearImage.addEventListener("click", () => {
    pendingImageFile = null;
    evalImageInput.value = "";
    evalPreview.classList.add("hidden");
    updateEvalBtn();
  });

  // File upload (.txt / .csv)
  evalFileInput.addEventListener("change", () => {
    const file = evalFileInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      // Parse CSV or text: take first column, skip header if it looks like one
      const lines = text.split("\n").map(l => l.split(",")[0].trim()).filter(l => l && l.length > 1);
      // Skip if first line looks like a header
      const first = lines[0] ? lines[0].toLowerCase() : "";
      if (first === "card" || first === "name" || first === "card name" || first === "card_name") {
        lines.shift();
      }
      evalCardList.value = lines.join("\n");
      updateEvalBtn();
    };
    reader.readAsText(file);
  });

  // Evaluate button
  evalBtn.addEventListener("click", async () => {
    if (!currentDeckUrl || !llmConfigured) return;

    evalBtn.disabled = true;
    evalStatus.classList.add("hidden");
    evalOutput.classList.add("hidden");
    evalOutput.innerHTML = "";

    let cardNames = [];

    // Step 1: If image, identify cards first
    if (pendingImageFile) {
      evalLoading.classList.remove("hidden");
      evalLoadingText.textContent = "Identifying cards from image…";

      try {
        const formData = new FormData();
        formData.append("image", pendingImageFile);
        const resp = await fetch("/api/identify-cards", { method: "POST", body: formData });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || "Image identification failed");
        cardNames = data.cards || [];
        // Put them in the text area
        evalCardList.value = cardNames.join("\n");
        updateEvalBtn();
      } catch (err) {
        evalStatus.textContent = "Image identification error: " + err.message;
        evalStatus.className = "ai-status error";
        evalStatus.classList.remove("hidden");
        evalLoading.classList.add("hidden");
        evalBtn.disabled = false;
        return;
      }
    }

    // Step 2: Get card list from textarea if not from image
    if (cardNames.length === 0) {
      cardNames = evalCardList.value.trim().split("\n").map(l => l.trim()).filter(l => l);
    }

    if (cardNames.length === 0) {
      evalStatus.textContent = "No cards to evaluate.";
      evalStatus.className = "ai-status error";
      evalStatus.classList.remove("hidden");
      evalLoading.classList.add("hidden");
      evalBtn.disabled = false;
      return;
    }

    // Step 3: Stream evaluation
    evalLoading.classList.remove("hidden");
    evalLoadingText.textContent = `Evaluating ${cardNames.length} card(s) against your deck…`;

    try {
      const resp = await fetch("/api/evaluate-cards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          deck_url: currentDeckUrl,
          cards: cardNames,
          add_threshold: parseFloat(document.getElementById("add-threshold").value),
          cut_threshold: parseFloat(document.getElementById("cut-threshold").value),
        }),
      });

      if (!resp.ok) {
        const errData = await resp.json();
        throw new Error(errData.error || "Evaluation failed");
      }

      evalOutput.classList.remove("hidden");
      evalLoading.classList.add("hidden");

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let rawMd = "";
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() || "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith("data: ")) continue;
          const payload = trimmed.slice(6);
          if (payload === "[DONE]") continue;
          try {
            const chunk = JSON.parse(payload);
            if (chunk.error) throw new Error(chunk.error);
            if (chunk.text) {
              rawMd += chunk.text;
              evalOutput.innerHTML = renderMarkdown(rawMd);
              evalOutput.scrollTop = evalOutput.scrollHeight;
            }
          } catch (pe) {
            if (pe.message && !pe.message.includes("JSON")) throw pe;
          }
        }
      }
    } catch (err) {
      evalStatus.textContent = err.message;
      evalStatus.className = "ai-status error";
      evalStatus.classList.remove("hidden");
      evalLoading.classList.add("hidden");
    } finally {
      evalBtn.disabled = false;
      evalLoading.classList.add("hidden");
    }
  });

  // ── Simple Markdown renderer ──
  function renderMarkdown(md) {
    let html = md
      // Escape HTML
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      // Headings
      .replace(/^#### (.+)$/gm, "<h4>$1</h4>")
      .replace(/^### (.+)$/gm, "<h3>$1</h3>")
      .replace(/^## (.+)$/gm, "<h2>$1</h2>")
      .replace(/^# (.+)$/gm, "<h1>$1</h1>")
      // Bold
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      // Italic
      .replace(/\*([^*]+)\*/g, "<em>$1</em>")
      // Inline code
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      // Horizontal rule
      .replace(/^---$/gm, "<hr>")
      // Unordered list items
      .replace(/^- (.+)$/gm, "<li>$1</li>")
      // Ordered list items
      .replace(/^\d+\. (.+)$/gm, "<li>$1</li>");

    // Wrap consecutive <li> in <ul>
    html = html.replace(/((?:<li>.*<\/li>\n?)+)/g, "<ul>$1</ul>");
    // Paragraphs: wrap remaining lines
    html = html.replace(/^(?!<[hulo]|<li|<hr)(.+)$/gm, "<p>$1</p>");
    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, "");
    return html;
  }
})();
