const $ = (id) => document.getElementById(id);

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  if (!response.ok) {
    throw new Error(data.detail || data.raw || response.statusText);
  }
  return data;
}

function renderMarkdownish(text) {
  return text
    .replace(/^## (.*)$/gm, "<h3>$1</h3>")
    .replace(/^- (.*)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, (block) => `<ul>${block}</ul>`)
    .replace(/_(.*?)_/g, "<em>$1</em>");
}

function parseSpeciesInput() {
  const raw = $("plot-species").value.trim();
  if (!raw) return [];
  return raw.split(/[,，\s]+/).map((s) => s.trim()).filter(Boolean);
}

function showPlots(images) {
  const gallery = $("plot-gallery");
  const cards = $("plot-cards");
  if (!images || !images.length) {
    gallery.classList.add("hidden");
    cards.innerHTML = "";
    return;
  }
  const stamp = Date.now();
  cards.innerHTML = images
    .map(
      (img) => `
      <figure class="plot-card">
        <figcaption>${img.label || img.filename}</figcaption>
        <img src="${img.url}?t=${stamp}" alt="${img.label || img.filename}" loading="lazy" />
      </figure>`,
    )
    .join("");
  gallery.classList.remove("hidden");
}

function plotsFromResult(plot) {
  if (!plot) return [];
  if (plot.images && plot.images.length) return plot.images;
  if (plot.image_url) return [{ label: "plot", url: plot.image_url, filename: "plot.png" }];
  return [];
}

function formatSimResult(data) {
  const lines = [
    `returncode: ${data.returncode}`,
    `command: ${data.command.join(" ")}`,
    "\n--- stdout ---\n",
    data.stdout || "(empty)",
    "\n--- stderr ---\n",
    data.stderr || "(empty)",
  ];
  if (data.plot) {
    if (data.plot.skipped) {
      lines.push("\n--- plot ---\n", `skipped: ${data.plot.reason}`);
    } else {
      lines.push(
        "\n--- plot ---\n",
        `returncode: ${data.plot.returncode}`,
        data.plot.stdout || "",
        data.plot.stderr || "",
      );
    }
  }
  return lines.join("\n");
}

async function loadHealth() {
  const el = $("health");
  try {
    const h = await api("/api/health");
    const bits = [
      h.molecules_loaded ? "分子库 OK" : "分子库缺失",
      h.reactions_loaded ? "反应库 OK" : "反应库缺失",
      h.nautilus_ready ? "Westlake 脚本 OK" : "Westlake 脚本缺失",
      h.tutorial_root ? `tutorial: ${h.tutorial_root}` : "",
    ];
    el.textContent = bits.filter(Boolean).join(" · ");
    el.className = "health " + (h.molecules_loaded && h.nautilus_ready ? "ok" : "warn");
  } catch (err) {
    el.textContent = `无法连接后端：${err.message}`;
    el.className = "health warn";
  }
}

let suggestTimer;
$("query").addEventListener("input", () => {
  clearTimeout(suggestTimer);
  const q = $("query").value.trim();
  const box = $("suggestions");
  if (q.length < 1) {
    box.classList.add("hidden");
    return;
  }
  suggestTimer = setTimeout(async () => {
    try {
      const { items } = await api(`/api/molecules/search?q=${encodeURIComponent(q)}&limit=8`);
      if (!items.length) {
        box.classList.add("hidden");
        return;
      }
      box.innerHTML = items
        .map(
          (m) =>
            `<button type="button" data-pick="${m.key}">${m.key} · ${m.normal_formula || ""} · ${m.smiles || ""}</button>`,
        )
        .join("");
      box.classList.remove("hidden");
      box.querySelectorAll("button").forEach((btn) => {
        btn.addEventListener("click", () => {
          $("query").value = btn.dataset.pick;
          $("plot-species").value = btn.dataset.pick;
          box.classList.add("hidden");
        });
      });
    } catch {
      box.classList.add("hidden");
    }
  }, 250);
});

$("query-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const summary = $("summary");
  summary.classList.remove("muted");
  summary.textContent = "查询中…";
  const button = event.submitter;
  button.disabled = true;
  try {
    const data = await api("/api/query", {
      method: "POST",
      body: JSON.stringify({
        query: $("query").value.trim(),
        include_reactions: $("include-reactions").checked,
        use_llm: $("use-llm").checked,
      }),
    });
    const header = data.resolved_key
      ? `解析为 **${data.resolved_key}**${data.llm_used ? "（Westlake LLM）" : "（规则摘要）"}\n\n`
      : "";
    summary.innerHTML = header + renderMarkdownish(data.summary || "无结果");
    if (data.resolved_key) {
      $("plot-species").value = data.resolved_key;
    }
  } catch (err) {
    summary.textContent = `查询失败：${err.message}`;
  } finally {
    button.disabled = false;
  }
});

$("preview-cmd").addEventListener("click", async () => {
  const out = $("sim-output");
  out.textContent = "加载命令…";
  try {
    const simDir = $("sim-dir").value.trim();
    const params = new URLSearchParams({
      use_evolution: $("use-evolution").checked,
    });
    if (simDir) params.set("sim_dir", simDir);
    const data = await api(`/api/simulation/preview?${params}`);
    out.textContent = [
      `cwd: ${data.cwd}`,
      `sim_dir: ${data.sim_dir}`,
      `command:\n  ${data.command.join(" ")}`,
    ].join("\n");
  } catch (err) {
    out.textContent = err.message;
  }
});

$("sim-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const out = $("sim-output");
  const button = event.submitter;
  button.disabled = true;
  out.textContent = "模拟运行中（Westlake + 绘图），可能需要数分钟…";
  showPlots([]);
  try {
    const simDir = $("sim-dir").value.trim();
    const species = parseSpeciesInput();
    const data = await api("/api/simulation/run", {
      method: "POST",
      body: JSON.stringify({
        sim_dir: simDir || null,
        use_evolution: $("use-evolution").checked,
        plot: $("plot-after-run").checked,
        plot_mode: $("plot-mode").value,
        species,
        extra_args: [],
      }),
    });
    out.textContent = formatSimResult(data);
    if (data.plot && data.plot.returncode === 0) {
      showPlots(plotsFromResult(data.plot));
    }
  } catch (err) {
    out.textContent = `运行失败：${err.message}`;
  } finally {
    button.disabled = false;
  }
});

$("plot-only").addEventListener("click", async () => {
  const out = $("sim-output");
  out.textContent = "绘图…";
  showPlots([]);
  try {
    const simDir = $("sim-dir").value.trim();
    const species = parseSpeciesInput();
    const data = await api("/api/simulation/plot", {
      method: "POST",
      body: JSON.stringify({
        sim_dir: simDir || null,
        species,
        plot_mode: $("plot-mode").value,
      }),
    });
    out.textContent = [
      `returncode: ${data.returncode}`,
      `mode: ${data.mode}`,
      `images: ${(data.images || []).length}`,
      data.stdout || "",
      data.stderr || "",
    ].join("\n");
    if (data.returncode === 0) {
      showPlots(plotsFromResult(data));
    }
  } catch (err) {
    out.textContent = `绘图失败：${err.message}`;
  }
});

loadHealth();
