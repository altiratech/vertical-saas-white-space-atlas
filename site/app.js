const MAX_COMPARE_ROWS = 3;

const state = {
  payload: null,
  rows: [],
  selectedCode: null,
  compareCodes: [],
};

async function load() {
  const response = await fetch("./data.json");
  const payload = await response.json();
  state.payload = payload;
  state.rows = payload.entities;
  state.selectedCode = state.rows[0]?.naics_code ?? null;
  state.compareCodes = [];

  bindControls(payload);
  renderSummary(payload);
  renderExplorer();
}

function bindControls(payload) {
  const moveFilter = document.querySelector("#move-filter");
  payload.filters.recommended_moves.forEach((move) => {
    const option = document.createElement("option");
    option.value = move;
    option.textContent = move;
    moveFilter.appendChild(option);
  });

  document.querySelector("#search-input").addEventListener("input", renderExplorer);
  document.querySelector("#move-filter").addEventListener("change", renderExplorer);
  document.querySelector("#confidence-filter").addEventListener("input", (event) => {
    document.querySelector("#confidence-value").textContent = `${event.target.value}+`;
    renderExplorer();
  });
  document.querySelector("#clear-shortlist").addEventListener("click", () => {
    state.compareCodes = [];
    renderExplorer();
  });
}

function renderExplorer() {
  renderShortlist();
  renderTable();
  renderDetail();
}

function renderSummary(payload) {
  document.querySelector("#method-version").textContent = payload.method_version;
  document.querySelector("#row-count").textContent = payload.summary.fully_joined_rows.toLocaleString();
  document.querySelector("#generated-at").textContent = new Date(payload.generated_at).toLocaleString();

  const cards = [
    {
      label: "Coverage",
      value: payload.summary.fully_joined_rows.toLocaleString(),
      detail: `${payload.summary.excluded_rows.toLocaleString()} rows are excluded today because one of the public sources or the NAICS bridge does not support a clean join.`,
    },
    {
      label: "Top Move",
      value: topMove(payload.summary.recommended_move_counts),
      detail: "Recommended moves are derived from software wedge, roll-up wedge, and confidence together.",
    },
    {
      label: "Software Range",
      value: payload.summary.software_wedge_range.map((value) => value.toFixed(1)).join(" - "),
      detail: "Score range across the full joined national table.",
    },
    {
      label: "Confidence",
      value: payload.summary.confidence_range.map((value) => value.toFixed(1)).join(" - "),
      detail: "Confidence drops when a 2022 industry needs a forward crosswalk from CBP 2017 anchors.",
    },
    {
      label: "Workflow Range",
      value: payload.summary.workflow_intensity_range.map((value) => value.toFixed(1)).join(" - "),
      detail: "Workflow intensity is derived from BLS industry occupation mix plus O*NET work activities.",
    },
  ];

  const summaryGrid = document.querySelector("#summary-grid");
  summaryGrid.innerHTML = cards
    .map(
      (card) => `
        <article class="summary-card">
          <p class="label">${card.label}</p>
          <strong>${card.value}</strong>
          <p>${card.detail}</p>
        </article>
      `
    )
    .join("");
}

function renderShortlist() {
  const compareRows = shortlistedRows();
  document.querySelector("#shortlist-count").textContent = `${compareRows.length} / ${MAX_COMPARE_ROWS} selected`;

  const chips = document.querySelector("#shortlist-chips");
  chips.innerHTML = compareRows.length
    ? compareRows
        .map(
          (row) => `
            <button class="shortlist-chip" type="button" data-remove-code="${row.naics_code}">
              <span>#${row.rank}</span>
              <strong>${row.entity_name}</strong>
            </button>
          `
        )
        .join("")
    : `<span class="shortlist-empty-chip">No markets shortlisted yet.</span>`;

  chips.querySelectorAll("[data-remove-code]").forEach((button) => {
    button.addEventListener("click", () => {
      toggleCompare(button.dataset.removeCode);
      renderExplorer();
    });
  });

  document.querySelector("#clear-shortlist").disabled = compareRows.length === 0;

  const comparePanel = document.querySelector("#compare-panel");
  if (!compareRows.length) {
    comparePanel.innerHTML = `
      <div class="compare-empty">
        <strong>Shortlist up to three markets.</strong>
        <p>Use the table to pin candidates, then compare workflow burden, buyer boundary, and watch-outs side by side.</p>
      </div>
    `;
  } else {
    const compareLead =
      compareRows.length === 1
        ? "Add one or two more markets to turn this shortlist into a real decision memo."
        : "Use this grid to answer why one shortlisted market deserves the next founder week over the others.";

    comparePanel.innerHTML = `
      <p class="compare-lead">${compareLead}</p>
      <div class="compare-grid">
        ${compareRows.map((row) => buildCompareCard(row)).join("")}
      </div>
    `;

    comparePanel.querySelectorAll("[data-remove-code]").forEach((button) => {
      button.addEventListener("click", () => {
        toggleCompare(button.dataset.removeCode);
        renderExplorer();
      });
    });
  }

  renderMemo(compareRows);
}

function renderMemo(compareRows) {
  const memoPanel = document.querySelector("#memo-panel");

  if (!compareRows.length) {
    memoPanel.innerHTML = `
      <div class="memo-empty">
        <strong>Decision memo appears after you shortlist markets.</strong>
        <p>Once you pin candidates, Atlas will draft a lightweight memo you can copy or download as markdown.</p>
      </div>
    `;
    return;
  }

  const memoText = buildMemoMarkdown(compareRows);

  memoPanel.innerHTML = `
    <div class="memo-header">
      <div>
        <p class="eyebrow">Memo Draft</p>
        <h3>Export a shortlist decision artifact</h3>
        <p class="memo-copy">
          This draft turns the current shortlist into a founder-ready memo with the leading pick, comparison table,
          and market-specific watch-outs grounded in the current public payload.
        </p>
      </div>
      <div class="memo-actions">
        <button id="copy-memo" class="secondary-button" type="button">Copy memo</button>
        <button id="download-memo" class="secondary-button" type="button">Download markdown</button>
        <span id="memo-status" class="memo-status">Ready</span>
      </div>
    </div>
    <pre class="memo-preview" id="memo-preview"></pre>
  `;

  document.querySelector("#memo-preview").textContent = memoText;
  document.querySelector("#copy-memo").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(memoText);
      updateMemoStatus("Copied");
    } catch (error) {
      updateMemoStatus("Copy failed");
    }
  });
  document.querySelector("#download-memo").addEventListener("click", () => {
    const blob = new Blob([memoText], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "atlas-shortlist-memo.md";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    updateMemoStatus("Downloaded");
  });
}

function updateMemoStatus(label) {
  const status = document.querySelector("#memo-status");
  if (status) {
    status.textContent = label;
  }
}

function buildCompareCard(row) {
  return `
    <article class="compare-card">
      <div class="compare-card-header">
        <div>
          <p class="eyebrow">#${row.rank} · ${row.recommended_move}</p>
          <h3>${row.entity_name}</h3>
          <p class="compare-code">${row.naics_code}</p>
        </div>
        <button class="secondary-button compare-remove" type="button" data-remove-code="${row.naics_code}">
          Remove
        </button>
      </div>

      <div class="compare-metrics">
        ${compareMetric("Software", row.scores.software_wedge.toFixed(1))}
        ${compareMetric("Roll-up", row.scores.rollup_wedge.toFixed(1))}
        ${compareMetric("Workflow", row.scores.workflow_intensity.toFixed(1))}
        ${compareMetric("Confidence", row.scores.confidence.toFixed(1))}
        ${compareMetric("Site Size", row.score_inputs.employees_per_establishment.toFixed(1))}
        ${compareMetric("BLS Pay", `$${row.anchors.bls_average_annual_pay_usd.toLocaleString()}`)}
      </div>

      <ul class="compare-notes">
        <li>
          <strong>Why It Fits</strong><br />
          <span>${firstPositiveSignal(row)}</span>
        </li>
        <li>
          <strong>Workflow Read</strong><br />
          <span>${workflowCompareLine(row)}</span>
        </li>
        <li>
          <strong>Buyer Boundary</strong><br />
          <span>${row.anchors.sba_size_standard.display} small-business ceiling on a ${formatBasis(row.anchors.sba_size_standard.basis)} basis.</span>
        </li>
        <li>
          <strong>Decision Risk</strong><br />
          <span>${decisionRisk(row)}</span>
        </li>
        <li>
          <strong>Confidence Note</strong><br />
          <span>${confidenceNote(row)}</span>
        </li>
      </ul>
    </article>
  `;
}

function buildMemoMarkdown(compareRows) {
  const orderedRows = [...compareRows].sort((left, right) => left.rank - right.rank);
  if (!orderedRows.length) {
    return "";
  }

  const leadRow = orderedRows[0];
  const shortlistNames = orderedRows.map((row) => `${row.entity_name} (${row.naics_code})`).join(", ");
  const generatedAt = new Date(state.payload.generated_at).toLocaleString();
  const comparisonTable = [
    "| Rank | NAICS | Industry | Move | Software | Roll-up | Workflow | Confidence |",
    "| --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
    ...orderedRows.map(
      (row) =>
        `| ${row.rank} | ${row.naics_code} | ${escapePipes(row.entity_name)} | ${row.recommended_move} | ${row.scores.software_wedge.toFixed(1)} | ${row.scores.rollup_wedge.toFixed(1)} | ${row.scores.workflow_intensity.toFixed(1)} | ${row.scores.confidence.toFixed(1)} |`
    ),
  ].join("\n");

  const marketSections = orderedRows
    .map(
      (row) => `## ${row.entity_name} (${row.naics_code})

- Current move: ${row.recommended_move}
- Why it fits: ${firstPositiveSignal(row)}
- Workflow read: ${workflowCompareLine(row)}
- Buyer boundary: ${row.anchors.sba_size_standard.display} ceiling on a ${formatBasis(row.anchors.sba_size_standard.basis)} basis
- Decision risk: ${decisionRisk(row)}
- Confidence note: ${confidenceNote(row)}
- Top visible occupation: ${topOccupationLine(row)}
`
    )
    .join("\n");

  return `# Vertical SaaS White-Space Atlas Shortlist Memo

Generated: ${generatedAt}
Method: ${state.payload.method_version}
Shortlist: ${shortlistNames}

## Current Recommendation

Best current pick inside this shortlist: **${leadRow.entity_name} (${leadRow.naics_code})**

Reason to lead with it: ${firstPositiveSignal(leadRow)}

Current watch-out: ${decisionRisk(leadRow)}

Confidence note: ${confidenceNote(leadRow)}

## Side-By-Side Comparison

${comparisonTable}

## Market Notes

${marketSections}
`.trim();
}

function compareMetric(label, value) {
  return `
    <div class="compare-metric">
      <span class="label">${label}</span>
      <strong>${value}</strong>
    </div>
  `;
}

function renderTable() {
  const tbody = document.querySelector("#industry-table");
  const filteredRows = currentRows();
  if (!filteredRows.length) {
    state.selectedCode = null;
    tbody.innerHTML = `
      <tr>
        <td colspan="7">No industries match the current filter set.</td>
      </tr>
    `;
    return;
  }

  if (!filteredRows.some((row) => row.naics_code === state.selectedCode)) {
    state.selectedCode = filteredRows[0].naics_code;
  }

  tbody.innerHTML = filteredRows.map((row) => buildTableRow(row)).join("");

  [...tbody.querySelectorAll("tr[data-naics-code]")].forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedCode = row.dataset.naicsCode;
      renderTable();
      renderDetail();
    });
  });

  [...tbody.querySelectorAll("[data-compare-code]")].forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleCompare(button.dataset.compareCode);
      renderExplorer();
    });
  });
}

function buildTableRow(row) {
  const disabled = !isCompared(row.naics_code) && state.compareCodes.length >= MAX_COMPARE_ROWS;
  const classes = [];
  if (row.naics_code === state.selectedCode) {
    classes.push("active");
  }
  if (isCompared(row.naics_code)) {
    classes.push("compared");
  }

  return `
    <tr data-naics-code="${row.naics_code}" class="${classes.join(" ")}">
      <td>${row.rank}</td>
      <td>
        <div class="industry-cell">
          <span class="industry-title">${row.entity_name}</span>
          <span class="industry-code">${row.naics_code}</span>
        </div>
      </td>
      <td>${row.scores.software_wedge.toFixed(1)}</td>
      <td>${row.scores.rollup_wedge.toFixed(1)}</td>
      <td>${row.recommended_move}</td>
      <td>${row.scores.confidence.toFixed(1)}</td>
      <td>
        <button
          type="button"
          class="compare-toggle ${isCompared(row.naics_code) ? "is-active" : ""}"
          data-compare-code="${row.naics_code}"
          ${disabled ? "disabled" : ""}
        >
          ${shortlistButtonLabel(row.naics_code, "table")}
        </button>
      </td>
    </tr>
  `;
}

function renderDetail() {
  const panel = document.querySelector("#detail-panel");
  const row = state.rows.find((item) => item.naics_code === state.selectedCode);
  if (!row) {
    panel.innerHTML = `<p class="detail-empty">No industry selected.</p>`;
    return;
  }

  const disabled = !isCompared(row.naics_code) && state.compareCodes.length >= MAX_COMPARE_ROWS;

  panel.innerHTML = `
    <div class="detail-header">
      <div>
        <p class="eyebrow">Industry Detail</p>
        <h2>${row.entity_name}</h2>
      </div>
      <button
        id="detail-shortlist-button"
        class="compare-toggle ${isCompared(row.naics_code) ? "is-active" : ""}"
        type="button"
        ${disabled ? "disabled" : ""}
      >
        ${shortlistButtonLabel(row.naics_code, "detail")}
      </button>
    </div>
    <div class="pill">${row.recommended_move}</div>
    <p class="lede">${row.summary}</p>

    <div class="detail-score-grid">
      <div class="detail-card">
        <p class="label">Software Wedge</p>
        <strong>${row.scores.software_wedge.toFixed(1)}</strong>
      </div>
      <div class="detail-card">
        <p class="label">Roll-up Wedge</p>
        <strong>${row.scores.rollup_wedge.toFixed(1)}</strong>
      </div>
      <div class="detail-card">
        <p class="label">Fragmentation</p>
        <strong>${row.scores.fragmentation.toFixed(1)}</strong>
      </div>
      <div class="detail-card">
        <p class="label">Thesis Fit</p>
        <strong>${row.scores.thesis_fit.toFixed(1)}</strong>
      </div>
      <div class="detail-card">
        <p class="label">Workflow</p>
        <strong>${row.scores.workflow_intensity.toFixed(1)}</strong>
      </div>
      <div class="detail-card">
        <p class="label">Confidence</p>
        <strong>${row.scores.confidence.toFixed(1)}</strong>
      </div>
    </div>

    <div class="detail-anchor-grid">
      <div class="detail-card">
        <p class="label">CBP Footprint</p>
        <strong>${row.anchors.cbp_establishments.toLocaleString()} estabs</strong>
        <span>${row.anchors.cbp_employment.toLocaleString()} employees</span>
      </div>
      <div class="detail-card">
        <p class="label">BLS Labor Pay</p>
        <strong>$${row.anchors.bls_average_annual_pay_usd.toLocaleString()}</strong>
        <span>${row.anchors.bls_employment_growth_pct.toFixed(1)}% employment growth</span>
      </div>
      <div class="detail-card">
        <p class="label">Average Site Size</p>
        <strong>${row.score_inputs.employees_per_establishment.toFixed(1)}</strong>
        <span>employees per establishment</span>
      </div>
      <div class="detail-card">
        <p class="label">SBA Threshold</p>
        <strong>${row.anchors.sba_size_standard.display}</strong>
        <span>${formatBasis(row.anchors.sba_size_standard.basis)} basis</span>
      </div>
    </div>

    <section>
      <p class="label">Decision Read</p>
      <ul class="detail-list">
        <li>
          <strong>Primary Risk</strong><br />
          <span>${decisionRisk(row)}</span>
        </li>
        <li>
          <strong>Confidence Note</strong><br />
          <span>${confidenceNote(row)}</span>
        </li>
      </ul>
    </section>

    <section>
      <p class="label">Fit Signals</p>
      <ul class="detail-list">
        ${
          row.score_inputs.thesis_fit_positive_signals.length
            ? row.score_inputs.thesis_fit_positive_signals
                .map(
                  (item) => `
                    <li>
                      <strong>Positive</strong><br />
                      <span>${item}</span>
                    </li>
                  `
                )
                .join("")
            : `
              <li>
                <strong>Positive</strong><br />
                <span>No strong positive thesis-fit signal surfaced beyond the structural data.</span>
              </li>
            `
        }
        ${
          row.score_inputs.thesis_fit_negative_signals.length
            ? row.score_inputs.thesis_fit_negative_signals
                .map(
                  (item) => `
                    <li>
                      <strong>Counter-signal</strong><br />
                      <span>${item}</span>
                    </li>
                  `
                )
                .join("")
            : ""
        }
      </ul>
    </section>

    <section>
      <p class="label">Workflow Profile</p>
      <ul class="detail-list">
        <li>
          <strong>Mapped Industry</strong><br />
          <span>${row.workflow_profile.matrix_industry_code} ${row.workflow_profile.matrix_industry_title}</span>
        </li>
        <li>
          <strong>Mapping Note</strong><br />
          <span>${row.workflow_profile.mapping_note}</span>
        </li>
        <li>
          <strong>Coverage</strong><br />
          <span>${row.workflow_profile.occupation_coverage_share_pct.toFixed(1)}% of industry employment is covered by the visible scored occupation mix.</span>
        </li>
        <li>
          <strong>Mix</strong><br />
          <span>
            Frontline operator share ${row.workflow_profile.frontline_operator_share_pct.toFixed(1)}%,
            knowledge-work share ${row.workflow_profile.knowledge_work_share_pct.toFixed(1)}%
          </span>
        </li>
        <li>
          <strong>Components</strong><br />
          <span>
            Documentation ${row.workflow_profile.component_scores.documentation.toFixed(1)},
            coordination ${row.workflow_profile.component_scores.coordination.toFixed(1)},
            compliance ${row.workflow_profile.component_scores.compliance.toFixed(1)},
            care/service ${row.workflow_profile.component_scores.care_service.toFixed(1)}
          </span>
        </li>
      </ul>
      <ul class="detail-list">
        ${row.workflow_profile.top_occupations
          .map(
            (item) => `
              <li>
                <strong>${item.occupation_title}</strong><br />
                <span>${item.occupation_code} · ${item.percent_of_industry.toFixed(1)}% of industry employment</span>
              </li>
            `
          )
          .join("")}
      </ul>
    </section>

    <section>
      <p class="label">Evidence</p>
      <ul class="detail-list">
        ${row.evidence
          .map(
            (item) => `
              <li>
                <strong>${item.label}</strong><br />
                <span>${item.detail}</span>
              </li>
            `
          )
          .join("")}
      </ul>
    </section>

    <section>
      <p class="label">Caveats</p>
      <ul class="detail-caveats">
        ${prioritizedCaveats(row).map((item) => `<li>${item}</li>`).join("")}
      </ul>
    </section>
  `;

  panel.querySelector("#detail-shortlist-button").addEventListener("click", () => {
    toggleCompare(row.naics_code);
    renderExplorer();
  });
}

function currentRows() {
  const query = document.querySelector("#search-input").value.trim().toLowerCase();
  const move = document.querySelector("#move-filter").value;
  const minConfidence = Number(document.querySelector("#confidence-filter").value);

  return state.rows.filter((row) => {
    const matchesQuery =
      !query ||
      row.entity_name.toLowerCase().includes(query) ||
      row.naics_code.includes(query);
    const matchesMove = move === "all" || row.recommended_move === move;
    const matchesConfidence = row.scores.confidence >= minConfidence;
    return matchesQuery && matchesMove && matchesConfidence;
  });
}

function shortlistedRows() {
  return state.compareCodes
    .map((code) => state.rows.find((row) => row.naics_code === code))
    .filter(Boolean);
}

function toggleCompare(code) {
  if (isCompared(code)) {
    state.compareCodes = state.compareCodes.filter((item) => item !== code);
    return;
  }
  if (state.compareCodes.length >= MAX_COMPARE_ROWS) {
    return;
  }
  state.compareCodes = [...state.compareCodes, code];
}

function isCompared(code) {
  return state.compareCodes.includes(code);
}

function shortlistButtonLabel(code, mode) {
  if (isCompared(code)) {
    return mode === "detail" ? "Remove from shortlist" : "Shortlisted";
  }
  if (state.compareCodes.length >= MAX_COMPARE_ROWS) {
    return "Shortlist full";
  }
  return mode === "detail" ? "Add to shortlist" : "Shortlist";
}

function firstPositiveSignal(row) {
  return (
    row.score_inputs.thesis_fit_positive_signals[0] ??
    "The structural data is directionally attractive, but no standout fit signal was surfaced."
  );
}

function prioritizedCaveats(row) {
  return [...row.caveats].sort((left, right) => caveatPriority(left) - caveatPriority(right));
}

function caveatPriority(caveat) {
  const priorities = [
    /broader published BLS parent industry/i,
    /closest published BLS parent industry/i,
    /visible BLS occupation mix/i,
    /differ materially/i,
    /workflow burden is inferred/i,
    /national-only slice/i,
  ];
  const matchIndex = priorities.findIndex((pattern) => pattern.test(caveat));
  return matchIndex === -1 ? priorities.length : matchIndex;
}

function decisionRisk(row) {
  if (row.score_inputs.thesis_fit_negative_signals.length) {
    return row.score_inputs.thesis_fit_negative_signals[0];
  }
  const caveat = prioritizedCaveats(row)[0];
  return humanizeCaveat(caveat);
}

function humanizeCaveat(caveat) {
  if (/broader published BLS parent industry/i.test(caveat)) {
    return "Workflow evidence is directional because BLS only publishes a broader parent industry for this NAICS line.";
  }
  if (/closest published BLS parent industry/i.test(caveat)) {
    return "Workflow evidence is directional because BLS rolls this NAICS line into a close parent industry.";
  }
  if (/visible BLS occupation mix/i.test(caveat)) {
    return "Workflow coverage is partial because some smaller or suppressed occupations are not visible in the public BLS mix.";
  }
  if (/differ materially/i.test(caveat)) {
    return "Employment scale is directional because CBP and BLS labor counts diverge materially for this line.";
  }
  if (/workflow burden is inferred/i.test(caveat)) {
    return "Workflow burden is inferred from public occupation mix rather than direct company workflow evidence.";
  }
  if (/national-only slice/i.test(caveat)) {
    return "Regional density and local regulatory variation are not yet represented in this national-only slice.";
  }
  return caveat;
}

function confidenceNote(row) {
  if (row.scores.confidence >= 90) {
    return "Confidence is high for this slice, but the result still abstracts away local market density.";
  }
  if (row.scores.confidence >= 80) {
    return "Confidence is solid, but at least one source bridge or workflow inference keeps the result directional rather than exact.";
  }
  return "Confidence is more directional here because source precision or public coverage is weaker than the top-ranked rows.";
}

function workflowCompareLine(row) {
  const topOccupation = row.workflow_profile.top_occupations[0];
  return `${topOccupation.occupation_title} is the top visible role at ${topOccupation.percent_of_industry.toFixed(1)}% of employment; frontline share is ${row.workflow_profile.frontline_operator_share_pct.toFixed(1)}% with ${row.workflow_profile.occupation_coverage_share_pct.toFixed(1)}% visible coverage.`;
}

function topOccupationLine(row) {
  const topOccupation = row.workflow_profile.top_occupations[0];
  return `${topOccupation.occupation_title} (${topOccupation.occupation_code}) at ${topOccupation.percent_of_industry.toFixed(1)}% of visible employment`;
}

function escapePipes(value) {
  return value.replaceAll("|", "\\|");
}

function formatBasis(basis) {
  return basis.replaceAll("_", " ");
}

function topMove(moveCounts) {
  return Object.entries(moveCounts)
    .sort((left, right) => right[1] - left[1])[0]?.[0] ?? "-";
}

load().catch((error) => {
  document.querySelector("#compare-panel").innerHTML = `
    <div class="compare-empty">
      <strong>Could not load site/data.json.</strong>
      <p>${error.message}</p>
    </div>
  `;
  document.querySelector("#memo-panel").innerHTML = `
    <div class="memo-empty">
      <strong>Memo preview unavailable.</strong>
      <p>${error.message}</p>
    </div>
  `;
  document.querySelector("#detail-panel").innerHTML = `
    <p class="detail-empty">Could not load site/data.json.</p>
    <pre>${error.message}</pre>
  `;
});
