const state = {
  payload: null,
  rows: [],
  selectedCode: null,
};

async function load() {
  const response = await fetch("./data.json");
  const payload = await response.json();
  state.payload = payload;
  state.rows = payload.entities;
  state.selectedCode = state.rows[0]?.naics_code ?? null;

  bindControls(payload);
  renderSummary(payload);
  renderTable();
  renderDetail();
}

function bindControls(payload) {
  const moveFilter = document.querySelector("#move-filter");
  payload.filters.recommended_moves.forEach((move) => {
    const option = document.createElement("option");
    option.value = move;
    option.textContent = move;
    moveFilter.appendChild(option);
  });

  document.querySelector("#search-input").addEventListener("input", renderTable);
  document.querySelector("#move-filter").addEventListener("change", renderTable);
  document.querySelector("#confidence-filter").addEventListener("input", (event) => {
    document.querySelector("#confidence-value").textContent = `${event.target.value}+`;
    renderTable();
  });
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

function renderTable() {
  const tbody = document.querySelector("#industry-table");
  const filteredRows = currentRows();
  if (!filteredRows.length) {
    tbody.innerHTML = `
      <tr>
        <td colspan="6">No industries match the current filter set.</td>
      </tr>
    `;
    document.querySelector("#detail-panel").innerHTML = `<p class="detail-empty">No industry selected.</p>`;
    return;
  }

  if (!filteredRows.some((row) => row.naics_code === state.selectedCode)) {
    state.selectedCode = filteredRows[0].naics_code;
  }

  tbody.innerHTML = filteredRows
    .map(
      (row) => `
        <tr data-naics-code="${row.naics_code}" class="${row.naics_code === state.selectedCode ? "active" : ""}">
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
        </tr>
      `
    )
    .join("");

  [...tbody.querySelectorAll("tr[data-naics-code]")].forEach((row) => {
    row.addEventListener("click", () => {
      state.selectedCode = row.dataset.naicsCode;
      renderTable();
      renderDetail();
    });
  });

  renderDetail();
}

function renderDetail() {
  const panel = document.querySelector("#detail-panel");
  const row = state.rows.find((item) => item.naics_code === state.selectedCode);
  if (!row) {
    panel.innerHTML = `<p class="detail-empty">No industry selected.</p>`;
    return;
  }

  panel.innerHTML = `
    <p class="eyebrow">Industry Detail</p>
    <h2>${row.entity_name}</h2>
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
        <span>${row.anchors.sba_size_standard.basis.replaceAll("_", " ")}</span>
      </div>
    </div>

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
        ${row.caveats.map((item) => `<li>${item}</li>`).join("")}
      </ul>
    </section>
  `;
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

function topMove(moveCounts) {
  return Object.entries(moveCounts)
    .sort((left, right) => right[1] - left[1])[0]?.[0] ?? "-";
}

load().catch((error) => {
  document.querySelector("#detail-panel").innerHTML = `
    <p class="detail-empty">Could not load site/data.json.</p>
    <pre>${error.message}</pre>
  `;
});
