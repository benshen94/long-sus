import {
  buildHeatmap,
  buildLineSeries,
  buildPyramidSeries,
  projectScenario,
  rowsToCsv,
} from "./runtime.mjs";
import { createInterventionStore } from "./interventions.mjs";


const state = {
  manifest: null,
  demography: null,
  analyticPresets: null,
  interventionStore: null,
  scenarioCatalog: [],
  activeResult: null,
  compareResult: null,
  renderToken: 0,
};


const elements = {
  pageShell: document.querySelector("[data-page-shell]"),
  loadStatus: document.getElementById("load-status"),
  loadError: document.getElementById("load-error"),
  presetInfoToggle: document.getElementById("preset-info-toggle"),
  presetHelp: document.getElementById("preset-help"),
  uptakeModeInfoToggle: document.getElementById("uptake-mode-info-toggle"),
  uptakeModeHelp: document.getElementById("uptake-mode-help"),
  presetSelect: document.getElementById("preset-select"),
  branchSelect: document.getElementById("branch-select"),
  targetSelect: document.getElementById("target-select"),
  factorSelectField: document.getElementById("factor-select-field"),
  factorSelect: document.getElementById("factor-select"),
  factorInputField: document.getElementById("factor-input-field"),
  factorInput: document.getElementById("factor-input"),
  heteroField: document.getElementById("hetero-field"),
  heteroMode: document.getElementById("hetero-mode"),
  analyticPresetField: document.getElementById("analytic-preset-field"),
  analyticPresetSelect: document.getElementById("analytic-preset-select"),
  launchYear: document.getElementById("launch-year"),
  projectionEndYear: document.getElementById("projection-end-year"),
  uptakeMode: document.getElementById("uptake-mode"),
  thresholdField: document.getElementById("threshold-field"),
  thresholdAge: document.getElementById("threshold-age"),
  startRuleField: document.getElementById("start-rule-field"),
  startRule: document.getElementById("start-rule"),
  bandEditor: document.getElementById("band-editor"),
  band2039: document.getElementById("band-20-39"),
  band4064: document.getElementById("band-40-64"),
  band65Plus: document.getElementById("band-65-plus"),
  schemeExplainer: document.getElementById("scheme-explainer"),
  comparePresetSelect: document.getElementById("compare-preset-select"),
  compareBranchSelect: document.getElementById("compare-branch-select"),
  compareTargetSelect: document.getElementById("compare-target-select"),
  compareFactorSelectField: document.getElementById("compare-factor-select-field"),
  compareFactorSelect: document.getElementById("compare-factor-select"),
  compareFactorInputField: document.getElementById("compare-factor-input-field"),
  compareFactorInput: document.getElementById("compare-factor-input"),
  compareHeteroField: document.getElementById("compare-hetero-field"),
  compareHeteroMode: document.getElementById("compare-hetero-mode"),
  compareAnalyticPresetField: document.getElementById("compare-analytic-preset-field"),
  compareAnalyticPresetSelect: document.getElementById("compare-analytic-preset-select"),
  compareToVanilla: document.getElementById("compare-to-vanilla"),
  compareExplainer: document.getElementById("compare-explainer"),
  yearSlider: document.getElementById("year-slider"),
  yearLabel: document.getElementById("year-label"),
  activeScenarioLabel: document.getElementById("active-scenario-label"),
  compareScenarioLabel: document.getElementById("compare-scenario-label"),
  heroMetrics: document.getElementById("hero-metrics"),
  pyramidChart: document.getElementById("pyramid-chart"),
  comparePyramidChart: document.getElementById("compare-pyramid-chart"),
  totalPopulationChart: document.getElementById("total-population-chart"),
  oldAgeShareChart: document.getElementById("old-age-share-chart"),
  treatedHeatmapChart: document.getElementById("treated-heatmap-chart"),
  survivalChart: document.getElementById("survival-chart"),
  exportScenarioCsv: document.getElementById("export-scenario-csv"),
  exportSummaryCsv: document.getElementById("export-summary-csv"),
  exportPyramidImage: document.getElementById("export-pyramid-image"),
  resetScenario: document.getElementById("reset-scenario"),
};


function setStatus(message) {
  if (!elements.loadStatus) {
    return;
  }
  elements.loadStatus.textContent = message;
}


function showError(message) {
  if (!elements.loadError) {
    return;
  }
  elements.loadError.hidden = false;
  elements.loadError.textContent = message;
}


function hideError() {
  if (!elements.loadError) {
    return;
  }
  elements.loadError.hidden = true;
  elements.loadError.textContent = "";
}


function formatFactor(value) {
  return `${Number(value).toFixed(2)}x`;
}


function formatPopulation(value) {
  const millions = value / 1_000_000;
  return `${millions.toFixed(1)}M`;
}


function formatPercent(value) {
  return `${(value * 100).toFixed(1)}%`;
}


function fillSelect(select, values, formatter = (value) => `${value}`) {
  select.innerHTML = "";
  for (const value of values) {
    const option = document.createElement("option");
    option.value = `${value}`;
    option.textContent = formatter(value);
    select.append(option);
  }
}


function fillPresetSelect(select) {
  select.innerHTML = "";
  for (const preset of state.scenarioCatalog) {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.label;
    select.append(option);
  }
}


function fillAnalyticPresetSelect(select) {
  select.innerHTML = "";
  for (const preset of state.analyticPresets.presets) {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.label;
    select.append(option);
  }
}


function findPreset(presetId) {
  const preset = state.scenarioCatalog.find((entry) => entry.id === presetId);
  if (!preset) {
    throw new Error(`Unknown preset: ${presetId}`);
  }
  return preset;
}


function findAnalyticPreset(presetId) {
  const safePresetId = presetId || state.manifest.default_analytic_preset_id;
  const preset = state.analyticPresets.presets.find((entry) => entry.id === safePresetId);
  if (!preset) {
    throw new Error(`Unknown analytic preset: ${safePresetId}`);
  }
  return preset;
}


function defaultFactorForTarget(target) {
  if (target === "Xc") {
    return Number(state.manifest.default_xc_factor);
  }
  return Number(state.manifest.default_eta_factor);
}


function branchLabel(branch) {
  return branch === "analytic_arm" ? "Analytic" : "SR";
}


function supportedBandedStartRules() {
  return ["absolute", "equal_probabilities", "uniform_start_age"];
}


function normalizeBandedStartRule(value) {
  if (supportedBandedStartRules().includes(value)) {
    return value;
  }
  return "absolute";
}


function presetDescription(preset) {
  const descriptions = {
    no_one: "No one is treated. This is the untreated baseline for comparison.",
    everyone: "Everyone is treated as soon as the intervention launches.",
    only_elderly_65plus: "Only ages 65 and above are eligible, and all of them start at the band edge.",
    "50pct_elderly_65plus": "Half of the 65+ population is treated.",
    "30pct_middle_40_64_plus_70pct_elderly_65plus": "Treatment starts for a smaller middle-age group and a larger elderly group.",
    half_population_adult_band: "Half of all adults 20+ are treated under one broad band.",
    prescription_bands_absolute: "Three age bands use fixed target shares and start immediately at each band edge.",
    prescription_bands_equal_probabilities: "Three age bands use equal yearly start probabilities within each band.",
    prescription_bands_uniform_start_age: "Three age bands use probabilities tuned to spread realized starts uniformly across each band.",
    threshold_age_60_all_eligible: "Everyone becomes eligible at age 60. Existing ages 60+ start at launch, and younger cohorts start when they cross 60.",
  };
  return descriptions[preset.id] || "Preset description unavailable.";
}


function uptakeModeDescription(mode) {
  if (mode === "threshold") {
    return "Threshold means everyone starts when they first reach one cutoff age. Existing eligible ages start at launch.";
  }
  return "Banded means each age band has its own target share, and the start rule decides how starts are distributed inside the band.";
}


function refreshHelpText() {
  const preset = findPreset(elements.presetSelect.value);
  if (elements.presetHelp) {
    elements.presetHelp.textContent = presetDescription(preset);
  }
  if (elements.uptakeModeHelp) {
    elements.uptakeModeHelp.textContent = `${uptakeModeDescription(elements.uptakeMode.value)} Presets prefill this, but you can still override it below.`;
  }
}


function toggleInlineHelp(button, panel) {
  if (!button || !panel) {
    return;
  }

  const nextExpanded = button.getAttribute("aria-expanded") !== "true";
  button.setAttribute("aria-expanded", `${nextExpanded}`);
  panel.hidden = !nextExpanded;
}


function connectHelpButtons() {
  const bindings = [
    [elements.uptakeModeInfoToggle, elements.uptakeModeHelp],
    [elements.presetInfoToggle, elements.presetHelp],
  ];

  for (const [button, panel] of bindings) {
    if (!button || !panel) {
      continue;
    }

    button.addEventListener("click", () => {
      toggleInlineHelp(button, panel);
    });
  }
}


function buildBandsFromInputs() {
  return [
    { start_age: 20, end_age: 39, target_share: Number(elements.band2039.value) / 100 },
    { start_age: 40, end_age: 64, target_share: Number(elements.band4064.value) / 100 },
    { start_age: 65, end_age: null, target_share: Number(elements.band65Plus.value) / 100 },
  ];
}


function applyPresetToActiveControls(presetId) {
  const preset = findPreset(presetId);
  elements.uptakeMode.value = preset.uptake_mode;
  elements.startRule.value = normalizeBandedStartRule(preset.start_rule_within_band);

  if (preset.threshold_age !== null && preset.threshold_age !== undefined) {
    elements.thresholdAge.value = `${preset.threshold_age}`;
  }

  const bands = preset.bands || state.manifest.default_bands;
  if (bands.length < 3) {
    return;
  }

  elements.band2039.value = `${Math.round(bands[0].target_share * 100)}`;
  elements.band4064.value = `${Math.round(bands[1].target_share * 100)}`;
  elements.band65Plus.value = `${Math.round(bands[2].target_share * 100)}`;
  refreshHelpText();
}


function updateFactorOptions(targetSelect, factorSelect, selectedValue = null) {
  const target = targetSelect.value;
  const factorGrid = state.manifest.factor_grids[target];
  if (!factorGrid) {
    targetSelect.value = state.manifest.default_target;
    return updateFactorOptions(targetSelect, factorSelect, selectedValue);
  }

  const options = factorGrid.map((value) => Number(value).toFixed(2));
  fillSelect(factorSelect, options, formatFactor);

  if (selectedValue !== null && options.includes(selectedValue)) {
    factorSelect.value = selectedValue;
    return;
  }

  factorSelect.value = Number(defaultFactorForTarget(target)).toFixed(2);
}


function syncFactorInput(targetSelect, factorInput, selectedValue = null) {
  const target = targetSelect.value;
  const factor = selectedValue === null ? defaultFactorForTarget(target) : Number(selectedValue);
  factorInput.value = Number(factor).toFixed(2);
}


function numericFactorValue(input, target) {
  const parsed = Number(input.value);
  if (Number.isFinite(parsed) && parsed > 0) {
    return parsed;
  }

  const fallback = defaultFactorForTarget(target);
  input.value = fallback.toFixed(2);
  return fallback;
}


function currentYear() {
  return Number(elements.yearSlider.value);
}


function buildScenarioName({
  presetId,
  target,
  factor,
  branch,
  heteroMode,
  analyticPresetId,
}) {
  if (target === null) {
    if (branch === "analytic_arm") {
      return `no_one_${branch}_${analyticPresetId}`;
    }
    if (heteroMode === "on") {
      return "no_one_hetero";
    }
    return "no_one";
  }

  const factorText = Number(factor).toFixed(2);
  if (branch === "analytic_arm") {
    return `${presetId}_${branch}_${analyticPresetId}_${target}_${factorText}x`;
  }

  const heteroSuffix = heteroMode === "on" ? "_hetero" : "";
  return `${presetId}_${target}_${factorText}x${heteroSuffix}`;
}


function buildActiveScenario() {
  const preset = findPreset(elements.presetSelect.value);
  const branch = state.manifest.default_branch;
  const isBaseline = preset.id === "no_one";
  const target = isBaseline ? null : elements.targetSelect.value;
  const factor = isBaseline
    ? 1.0
    : branch === "analytic_arm"
      ? numericFactorValue(elements.factorInput, elements.targetSelect.value)
      : Number(elements.factorSelect.value);
  const heteroMode = branch === "sr" ? elements.heteroMode.value : "off";
  const analyticPresetId = branch === "analytic_arm" ? elements.analyticPresetSelect.value : null;
  const uptakeMode = isBaseline ? "threshold" : elements.uptakeMode.value;
  const thresholdAge = uptakeMode === "threshold" && !isBaseline
    ? Number(elements.thresholdAge.value)
    : null;
  const bands = uptakeMode === "banded" ? buildBandsFromInputs() : [];
  const startRule = uptakeMode === "banded"
    ? normalizeBandedStartRule(elements.startRule.value)
    : "deterministic_threshold";

  return {
    name: buildScenarioName({
      presetId: preset.id,
      target,
      factor,
      branch,
      heteroMode,
      analyticPresetId,
    }),
    label: preset.label,
    scheme_id: preset.id,
    country: state.manifest.country,
    mode: "dynamic",
    launch_year: Number(elements.launchYear.value),
    projection_end_year: Number(elements.projectionEndYear.value),
    uptake_mode: uptakeMode,
    threshold_age: thresholdAge,
    bands,
    start_rule_within_band: startRule,
    target,
    factor,
    branch,
    analytic_preset_id: analyticPresetId,
    persistence_rule: "once_on_stay_on",
    demo_variant: "medium",
    migration_mode: "on",
    hetero_mode: heteroMode,
  };
}


function buildCompareScenario() {
  const preset = findPreset(elements.comparePresetSelect.value);
  const branch = state.manifest.default_branch;
  const isBaseline = preset.id === "no_one";
  const target = isBaseline ? null : elements.compareTargetSelect.value;
  const factor = isBaseline
    ? 1.0
    : branch === "analytic_arm"
      ? numericFactorValue(elements.compareFactorInput, elements.compareTargetSelect.value)
      : Number(elements.compareFactorSelect.value);
  const heteroMode = branch === "sr" ? elements.compareHeteroMode.value : "off";
  const analyticPresetId = branch === "analytic_arm" ? elements.compareAnalyticPresetSelect.value : null;
  const compareStartRule = preset.uptake_mode === "banded"
    ? normalizeBandedStartRule(preset.start_rule_within_band)
    : "deterministic_threshold";

  return {
    name: buildScenarioName({
      presetId: preset.id,
      target,
      factor,
      branch,
      heteroMode,
      analyticPresetId,
    }),
    label: preset.label,
    scheme_id: preset.id,
    country: state.manifest.country,
    mode: "dynamic",
    launch_year: Number(elements.launchYear.value),
    projection_end_year: Number(elements.projectionEndYear.value),
    uptake_mode: preset.uptake_mode,
    threshold_age: preset.threshold_age,
    bands: preset.bands || [],
    start_rule_within_band: compareStartRule,
    target,
    factor,
    branch,
    analytic_preset_id: analyticPresetId,
    persistence_rule: "once_on_stay_on",
    demo_variant: "medium",
    migration_mode: "on",
    hetero_mode: heteroMode,
  };
}


function updateControlVisibility() {
  const preset = findPreset(elements.presetSelect.value);
  const comparePreset = findPreset(elements.comparePresetSelect.value);
  const activeBranch = state.manifest.default_branch;
  const compareBranch = state.manifest.default_branch;
  const isBaseline = preset.id === "no_one";
  const compareIsBaseline = comparePreset.id === "no_one";

  elements.targetSelect.disabled = isBaseline;
  elements.factorSelect.disabled = true;
  elements.factorInput.disabled = isBaseline;
  elements.heteroMode.disabled = true;
  elements.analyticPresetSelect.disabled = false;
  elements.uptakeMode.disabled = isBaseline;

  elements.factorSelectField.hidden = true;
  elements.factorInputField.hidden = false;
  elements.heteroField.hidden = true;
  elements.analyticPresetField.hidden = false;

  const uptakeMode = isBaseline ? "threshold" : elements.uptakeMode.value;
  elements.thresholdField.hidden = uptakeMode !== "threshold";
  elements.startRuleField.hidden = uptakeMode !== "banded";
  elements.bandEditor.hidden = uptakeMode !== "banded";

  elements.compareTargetSelect.disabled = compareIsBaseline;
  elements.compareFactorSelect.disabled = true;
  elements.compareFactorInput.disabled = compareIsBaseline;
  elements.compareHeteroMode.disabled = true;
  elements.compareAnalyticPresetSelect.disabled = false;

  elements.compareFactorSelectField.hidden = true;
  elements.compareFactorInputField.hidden = false;
  elements.compareHeteroField.hidden = true;
  elements.compareAnalyticPresetField.hidden = false;

  const descriptions = {
    threshold: "Everyone at or above the threshold starts at launch. Later cohorts start when they cross that age.",
    absolute: "The chosen share starts at the lower edge of each band, or at launch if already inside the band.",
    equal_probabilities: "Each year inside the band has the same start probability.",
    uniform_start_age: "Start probabilities are tuned so realized start age is uniform inside the band.",
  };

  if (isBaseline) {
    elements.schemeExplainer.textContent = `Untreated baseline on the ${branchLabel(activeBranch)} branch.`;
  } else if (uptakeMode === "threshold") {
    elements.schemeExplainer.textContent = `${descriptions.threshold} Branch: ${branchLabel(activeBranch)}.`;
  } else {
    const startRule = normalizeBandedStartRule(elements.startRule.value);
    elements.schemeExplainer.textContent = `${descriptions[startRule]} Branch: ${branchLabel(activeBranch)}.`;
  }

  if (compareIsBaseline) {
    elements.compareExplainer.textContent = `Comparison scenario is the untreated baseline on the ${branchLabel(compareBranch)} branch.`;
    return;
  }

  if (comparePreset.uptake_mode === "threshold") {
    elements.compareExplainer.textContent = `${descriptions.threshold} Branch: ${branchLabel(compareBranch)}.`;
    return;
  }

  const compareStartRule = normalizeBandedStartRule(comparePreset.start_rule_within_band);
  elements.compareExplainer.textContent = `${descriptions[compareStartRule]} Branch: ${branchLabel(compareBranch)}.`;
  refreshHelpText();
}


function updateYearRange(maxYear) {
  elements.yearSlider.min = `${state.demography.years[0]}`;
  elements.yearSlider.max = `${maxYear}`;

  const current = Number(elements.yearSlider.value || maxYear);
  const safeYear = Math.min(Math.max(current, state.demography.years[0]), maxYear);
  elements.yearSlider.value = `${safeYear}`;
  elements.yearLabel.textContent = `${safeYear}`;
}


function activeSummaryRow() {
  const year = currentYear();
  return state.activeResult.summaryRows.find((row) => row.year === year);
}


function renderHeroMetrics() {
  if (!elements.heroMetrics) {
    return;
  }

  const summary = activeSummaryRow();
  const cards = [
    ["Population", formatPopulation(summary.total_population)],
    ["Treated share", formatPercent(summary.treated_share)],
    ["Age 65+", formatPercent(summary.old_age_share_65_plus)],
    ["Median age", `${summary.median_age.toFixed(0)}`],
  ];

  elements.heroMetrics.innerHTML = cards.map(([label, value]) => {
    return `
      <div class="metric-tile">
        <span class="metric-label">${label}</span>
        <strong class="metric-value">${value}</strong>
      </div>
    `;
  }).join("");
}


function renderPyramid(plotElement, result, year, titleText) {
  if (!plotElement) {
    return;
  }

  const series = buildPyramidSeries(result, year);
  const maleTotal = series.male.map((value) => -(value / 1_000_000));
  const femaleTotal = series.female.map((value) => value / 1_000_000);
  const maleTreated = series.treatedMale.map((value) => -(value / 1_000_000));
  const femaleTreated = series.treatedFemale.map((value) => value / 1_000_000);

  const traces = [
    {
      type: "bar",
      orientation: "h",
      y: series.ages,
      x: maleTotal,
      marker: { color: "#3b5b92" },
      opacity: 0.5,
      name: "Male total",
    },
    {
      type: "bar",
      orientation: "h",
      y: series.ages,
      x: femaleTotal,
      marker: { color: "#df6d57" },
      opacity: 0.5,
      name: "Female total",
    },
    {
      type: "bar",
      orientation: "h",
      y: series.ages,
      x: maleTreated,
      marker: { color: "#16314d" },
      name: "Male treated",
    },
    {
      type: "bar",
      orientation: "h",
      y: series.ages,
      x: femaleTreated,
      marker: { color: "#8e2f21" },
      name: "Female treated",
    },
  ];

  const maxValue = Math.max(
    ...series.male.map((value) => value / 1_000_000),
    ...series.female.map((value) => value / 1_000_000),
    1,
  );
  const axisTicks = [-maxValue, -maxValue / 2, 0, maxValue / 2, maxValue];

  Plotly.react(plotElement, traces, {
    title: { text: titleText, font: { family: "Instrument Serif", size: 24 } },
    barmode: "overlay",
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 60, r: 30, t: 54, b: 88 },
    xaxis: {
      title: "Population (millions)",
      zeroline: true,
      zerolinecolor: "#5f625c",
      gridcolor: "#d7d0c2",
      tickvals: axisTicks,
      ticktext: axisTicks.map((value) => Math.abs(value).toFixed(1)),
    },
    yaxis: {
      title: "Age",
      gridcolor: "#ece4d7",
    },
    legend: {
      orientation: "h",
      x: 0.5,
      xanchor: "center",
      y: -0.18,
      yanchor: "top",
      bgcolor: "rgba(0,0,0,0)",
    },
    transition: { duration: 220, easing: "cubic-out" },
  }, { responsive: true, displayModeBar: false });
}


function renderLineCharts() {
  if (!elements.totalPopulationChart || !elements.oldAgeShareChart) {
    return;
  }

  const activeTotal = buildLineSeries(state.activeResult, "total_population");
  const compareTotal = buildLineSeries(state.compareResult, "total_population");
  const activeOldAge = buildLineSeries(state.activeResult, "old_age_share_65_plus");
  const compareOldAge = buildLineSeries(state.compareResult, "old_age_share_65_plus");

  Plotly.react(elements.totalPopulationChart, [
    {
      x: activeTotal.x,
      y: activeTotal.y.map((value) => value / 1_000_000),
      type: "scatter",
      mode: "lines",
      line: { color: "#16314d", width: 3 },
      name: "Active scenario",
    },
    {
      x: compareTotal.x,
      y: compareTotal.y.map((value) => value / 1_000_000),
      type: "scatter",
      mode: "lines",
      line: { color: "#d35f3d", width: 3, dash: "dot" },
      name: "Comparison scenario",
    },
  ], {
    title: { text: "Total population over time", font: { family: "Instrument Serif", size: 22 } },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 56, r: 20, t: 48, b: 78 },
    xaxis: { title: "Year", gridcolor: "#ece4d7" },
    yaxis: { title: "Millions", gridcolor: "#d7d0c2" },
    legend: { orientation: "h", x: 0.5, xanchor: "center", y: -0.18, yanchor: "top", bgcolor: "rgba(0,0,0,0)" },
  }, { responsive: true, displayModeBar: false });

  Plotly.react(elements.oldAgeShareChart, [
    {
      x: activeOldAge.x,
      y: activeOldAge.y.map((value) => value * 100),
      type: "scatter",
      mode: "lines",
      line: { color: "#16314d", width: 3 },
      name: "Active scenario",
    },
    {
      x: compareOldAge.x,
      y: compareOldAge.y.map((value) => value * 100),
      type: "scatter",
      mode: "lines",
      line: { color: "#d35f3d", width: 3, dash: "dot" },
      name: "Comparison scenario",
    },
  ], {
    title: { text: "Population share age 65+", font: { family: "Instrument Serif", size: 22 } },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 56, r: 20, t: 48, b: 78 },
    xaxis: { title: "Year", gridcolor: "#ece4d7" },
    yaxis: { title: "Percent", gridcolor: "#d7d0c2" },
    legend: { orientation: "h", x: 0.5, xanchor: "center", y: -0.18, yanchor: "top", bgcolor: "rgba(0,0,0,0)" },
  }, { responsive: true, displayModeBar: false });
}


function renderHeatmap() {
  if (!elements.treatedHeatmapChart) {
    return;
  }

  const heatmap = buildHeatmap(state.activeResult);
  Plotly.react(elements.treatedHeatmapChart, [{
    z: heatmap.values,
    x: heatmap.years,
    y: heatmap.ages,
    type: "heatmap",
    colorscale: [
      [0, "#efe8da"],
      [0.35, "#caa177"],
      [0.7, "#c25a3c"],
      [1, "#641f16"],
    ],
    zmin: 0,
    zmax: 1,
    hovertemplate: "Year %{x}<br>Age %{y}<br>Treated share %{z:.1%}<extra></extra>",
    colorbar: { title: "Treated share" },
  }], {
    title: { text: "Share of each age-year cell treated", font: { family: "Instrument Serif", size: 22 } },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 56, r: 30, t: 48, b: 44 },
    xaxis: { title: "Year" },
    yaxis: { title: "Age" },
  }, { responsive: true, displayModeBar: false });
}


function renderSurvivalChart() {
  if (!elements.survivalChart) {
    return;
  }

  const ages = state.activeResult.survivalCurve.map((_, index) => index);
  Plotly.react(elements.survivalChart, [
    {
      x: ages,
      y: state.activeResult.survivalCurve.map((value) => value * 1000),
      type: "scatter",
      mode: "lines",
      line: { color: "#16314d", width: 3 },
      name: "Active scenario",
    },
    {
      x: ages,
      y: state.compareResult.survivalCurve.map((value) => value * 1000),
      type: "scatter",
      mode: "lines",
      line: { color: "#d35f3d", width: 3, dash: "dot" },
      name: "Comparison scenario",
    },
  ], {
    title: { text: "Cohort survival curves", font: { family: "Instrument Serif", size: 22 } },
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 56, r: 20, t: 48, b: 78 },
    xaxis: { title: "Age", gridcolor: "#ece4d7" },
    yaxis: { title: "People alive per 1000", gridcolor: "#d7d0c2" },
    legend: { orientation: "h", x: 0.5, xanchor: "center", y: -0.18, yanchor: "top", bgcolor: "rgba(0,0,0,0)" },
  }, { responsive: true, displayModeBar: false });
}


function scenarioHeadline(scenario) {
  const branchText = branchLabel(scenario.branch);
  if (scenario.target === null) {
    return `${scenario.label} | ${branchText} | launch ${scenario.launch_year}`;
  }

  if (scenario.branch === "analytic_arm") {
    const preset = findAnalyticPreset(scenario.analytic_preset_id);
    return `${scenario.label} | ${branchText} ${preset.label} | ${scenario.target} ${formatFactor(scenario.factor)} | launch ${scenario.launch_year}`;
  }

  return `${scenario.label} | ${branchText} ${scenario.target} ${formatFactor(scenario.factor)} | launch ${scenario.launch_year}`;
}


function renderScenarioLabels(activeScenario, compareScenario) {
  if (elements.activeScenarioLabel) {
    elements.activeScenarioLabel.textContent = scenarioHeadline(activeScenario);
  }
  if (elements.compareScenarioLabel) {
    elements.compareScenarioLabel.textContent = scenarioHeadline(compareScenario);
  }
}


function updateUrl(activeScenario, compareScenario, selectedYear) {
  const params = new URLSearchParams();
  params.set("preset", activeScenario.scheme_id);
  params.set("branch", activeScenario.branch);
  params.set("target", activeScenario.target || "none");
  params.set("factor", activeScenario.factor.toFixed(2));
  params.set("hetero", activeScenario.hetero_mode);
  params.set("analyticPreset", activeScenario.analytic_preset_id || "");
  params.set("launch", `${activeScenario.launch_year}`);
  params.set("end", `${activeScenario.projection_end_year}`);
  params.set("uptake", activeScenario.uptake_mode);
  params.set("threshold", `${activeScenario.threshold_age ?? -1}`);
  params.set("startRule", activeScenario.start_rule_within_band);
  params.set("band2039", elements.band2039.value);
  params.set("band4064", elements.band4064.value);
  params.set("band65", elements.band65Plus.value);
  params.set("comparePreset", compareScenario.scheme_id);
  params.set("compareBranch", compareScenario.branch);
  params.set("compareTarget", compareScenario.target || "none");
  params.set("compareFactor", compareScenario.factor.toFixed(2));
  params.set("compareHetero", compareScenario.hetero_mode);
  params.set("compareAnalyticPreset", compareScenario.analytic_preset_id || "");
  params.set("year", `${selectedYear}`);
  history.replaceState(null, "", `?${params.toString()}`);
}


function setControlsFromUrl() {
  const params = new URLSearchParams(window.location.search);

  if (params.has("preset")) {
    elements.presetSelect.value = params.get("preset");
    applyPresetToActiveControls(elements.presetSelect.value);
  }
  if (params.has("branch")) {
    elements.branchSelect.value = params.get("branch");
  }
  if (params.has("target") && params.get("target") !== "none") {
    elements.targetSelect.value = params.get("target");
  }
  if (params.has("factor")) {
    updateFactorOptions(elements.targetSelect, elements.factorSelect, params.get("factor"));
    syncFactorInput(elements.targetSelect, elements.factorInput, params.get("factor"));
  }
  if (params.has("hetero")) {
    elements.heteroMode.value = params.get("hetero");
  }
  if (params.has("analyticPreset") && params.get("analyticPreset")) {
    elements.analyticPresetSelect.value = params.get("analyticPreset");
  }
  if (params.has("launch")) {
    elements.launchYear.value = params.get("launch");
  }
  if (params.has("end")) {
    elements.projectionEndYear.value = params.get("end");
  }
  if (params.has("uptake")) {
    elements.uptakeMode.value = params.get("uptake");
  }
  if (params.has("threshold")) {
    elements.thresholdAge.value = params.get("threshold");
  }
  if (params.has("startRule")) {
    elements.startRule.value = normalizeBandedStartRule(params.get("startRule"));
  }
  if (params.has("band2039")) {
    elements.band2039.value = params.get("band2039");
  }
  if (params.has("band4064")) {
    elements.band4064.value = params.get("band4064");
  }
  if (params.has("band65")) {
    elements.band65Plus.value = params.get("band65");
  }

  if (params.has("comparePreset")) {
    elements.comparePresetSelect.value = params.get("comparePreset");
  }
  if (params.has("compareBranch")) {
    elements.compareBranchSelect.value = params.get("compareBranch");
  }
  if (params.has("compareTarget") && params.get("compareTarget") !== "none") {
    elements.compareTargetSelect.value = params.get("compareTarget");
  }
  if (params.has("compareFactor")) {
    updateFactorOptions(elements.compareTargetSelect, elements.compareFactorSelect, params.get("compareFactor"));
    syncFactorInput(elements.compareTargetSelect, elements.compareFactorInput, params.get("compareFactor"));
  }
  if (params.has("compareHetero")) {
    elements.compareHeteroMode.value = params.get("compareHetero");
  }
  if (params.has("compareAnalyticPreset") && params.get("compareAnalyticPreset")) {
    elements.compareAnalyticPresetSelect.value = params.get("compareAnalyticPreset");
  }
  if (params.has("year")) {
    elements.yearSlider.value = params.get("year");
  }
}


async function projectAndRender() {
  hideError();
  setStatus("Updating scenario");

  const renderToken = state.renderToken + 1;
  state.renderToken = renderToken;

  const activeScenario = buildActiveScenario();
  const compareScenario = buildCompareScenario();

  const [activeIntervention, compareIntervention] = await Promise.all([
    state.interventionStore.getAsset(activeScenario),
    state.interventionStore.getAsset(compareScenario),
  ]);

  if (renderToken !== state.renderToken) {
    return;
  }

  state.activeResult = projectScenario(state.demography, activeScenario, activeIntervention);
  state.compareResult = projectScenario(state.demography, compareScenario, compareIntervention);

  const maxYear = Math.min(activeScenario.projection_end_year, compareScenario.projection_end_year);
  updateYearRange(maxYear);

  const selectedYear = currentYear();
  renderScenarioLabels(activeScenario, compareScenario);
  renderHeroMetrics();
  renderPyramid(elements.pyramidChart, state.activeResult, selectedYear, `Active scenario · ${selectedYear}`);
  renderPyramid(elements.comparePyramidChart, state.compareResult, selectedYear, `Comparison scenario · ${selectedYear}`);
  renderLineCharts();
  renderHeatmap();
  renderSurvivalChart();
  updateUrl(activeScenario, compareScenario, selectedYear);
  setStatus("Ready");
}


async function rerender() {
  try {
    updateControlVisibility();
    await projectAndRender();
  } catch (error) {
    console.error(error);
    setStatus("Update failed");
    showError(error.message || "Scenario update failed");
  }
}


function downloadFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}


function connectExports() {
  elements.exportScenarioCsv.addEventListener("click", () => {
    const content = rowsToCsv(state.activeResult.populationRows);
    downloadFile("population_by_year_age.csv", content, "text/csv;charset=utf-8");
  });

  elements.exportSummaryCsv.addEventListener("click", () => {
    const content = rowsToCsv(state.activeResult.summaryRows);
    downloadFile("summary.csv", content, "text/csv;charset=utf-8");
  });

  elements.exportPyramidImage.addEventListener("click", async () => {
    await Plotly.downloadImage(elements.pyramidChart, {
      format: "png",
      filename: "world_analytic_pyramid",
      width: 1200,
      height: 900,
    });
  });

  elements.resetScenario.addEventListener("click", async () => {
    elements.presetSelect.value = state.manifest.default_preset_id;
    elements.comparePresetSelect.value = state.manifest.default_compare_preset_id;
    elements.branchSelect.value = state.manifest.default_branch;
    elements.compareBranchSelect.value = state.manifest.default_branch;
    elements.targetSelect.value = state.manifest.default_target;
    elements.compareTargetSelect.value = state.manifest.default_target;
    updateFactorOptions(elements.targetSelect, elements.factorSelect);
    updateFactorOptions(elements.compareTargetSelect, elements.compareFactorSelect, "1.00");
    syncFactorInput(elements.targetSelect, elements.factorInput);
    syncFactorInput(elements.compareTargetSelect, elements.compareFactorInput, "1.00");
    elements.heteroMode.value = "off";
    elements.compareHeteroMode.value = "off";
    elements.analyticPresetSelect.value = state.manifest.default_analytic_preset_id;
    elements.compareAnalyticPresetSelect.value = state.manifest.default_analytic_preset_id;
    elements.launchYear.value = `${state.manifest.default_launch_year}`;
    elements.projectionEndYear.value = `${state.manifest.default_projection_end_year}`;
    applyPresetToActiveControls(elements.presetSelect.value);
    refreshHelpText();
    await rerender();
  });

  elements.compareToVanilla.addEventListener("click", async () => {
    elements.comparePresetSelect.value = "no_one";
    elements.compareBranchSelect.value = state.manifest.default_branch;
    elements.compareTargetSelect.value = state.manifest.default_target;
    updateFactorOptions(elements.compareTargetSelect, elements.compareFactorSelect, "1.00");
    syncFactorInput(elements.compareTargetSelect, elements.compareFactorInput, "1.00");
    elements.compareHeteroMode.value = "off";
    elements.compareAnalyticPresetSelect.value = state.manifest.default_analytic_preset_id;
    await rerender();
  });
}


function connectInputs() {
  elements.presetSelect.addEventListener("change", async () => {
    applyPresetToActiveControls(elements.presetSelect.value);
    await rerender();
  });

  elements.comparePresetSelect.addEventListener("change", rerender);

  elements.targetSelect.addEventListener("change", async () => {
    updateFactorOptions(elements.targetSelect, elements.factorSelect);
    syncFactorInput(elements.targetSelect, elements.factorInput);
    await rerender();
  });

  elements.compareTargetSelect.addEventListener("change", async () => {
    updateFactorOptions(elements.compareTargetSelect, elements.compareFactorSelect);
    syncFactorInput(elements.compareTargetSelect, elements.compareFactorInput);
    await rerender();
  });

  [
    elements.factorSelect,
    elements.factorInput,
    elements.heteroMode,
    elements.analyticPresetSelect,
    elements.launchYear,
    elements.projectionEndYear,
    elements.uptakeMode,
    elements.thresholdAge,
    elements.startRule,
    elements.band2039,
    elements.band4064,
    elements.band65Plus,
    elements.compareFactorSelect,
    elements.compareFactorInput,
    elements.compareHeteroMode,
    elements.compareAnalyticPresetSelect,
  ].forEach((element) => {
    element.addEventListener("change", rerender);
  });

  elements.yearSlider.addEventListener("input", () => {
    const selectedYear = currentYear();
    elements.yearLabel.textContent = `${selectedYear}`;
    renderHeroMetrics();
    renderPyramid(elements.pyramidChart, state.activeResult, selectedYear, `Active scenario · ${selectedYear}`);
    renderPyramid(elements.comparePyramidChart, state.compareResult, selectedYear, `Comparison scenario · ${selectedYear}`);
    updateUrl(buildActiveScenario(), buildCompareScenario(), selectedYear);
  });
}


async function loadAssets() {
  if (window.location.protocol === "file:") {
    showError("Open this dashboard through GitHub Pages or a local HTTP server. Browsers block asset fetches from file://.");
  }

  setStatus("Loading assets");
  const manifestUrl = new URL("./assets/manifest.json", window.location.href);

  const fetchJson = async (url) => {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to load ${url}`);
    }
    return response.json();
  };

  state.manifest = await fetchJson(manifestUrl);

  const resolvePath = (relativePath) => new URL(relativePath, manifestUrl).href;
  state.manifest.paths.demography = resolvePath(state.manifest.paths.demography);
  state.manifest.paths.sr_interventions_root = resolvePath(state.manifest.paths.sr_interventions_root);
  state.manifest.paths.analytic_presets = resolvePath(state.manifest.paths.analytic_presets);
  state.manifest.paths.scenario_catalog = resolvePath(state.manifest.paths.scenario_catalog);

  const [demography, analyticPresets, scenarioCatalog] = await Promise.all([
    fetchJson(state.manifest.paths.demography),
    fetchJson(state.manifest.paths.analytic_presets),
    fetchJson(state.manifest.paths.scenario_catalog),
  ]);

  state.demography = demography;
  state.analyticPresets = analyticPresets;
  state.scenarioCatalog = scenarioCatalog.presets;
  state.interventionStore = createInterventionStore({
    manifest: state.manifest,
    demography: state.demography,
    analyticPresets: state.analyticPresets,
    fetchJson,
  });
}


function populateControls() {
  fillSelect(elements.launchYear, state.demography.years);
  fillSelect(elements.projectionEndYear, state.demography.years.slice(1));
  fillSelect(elements.branchSelect, state.manifest.branch_options, branchLabel);
  fillSelect(elements.compareBranchSelect, state.manifest.branch_options, branchLabel);
  fillSelect(elements.targetSelect, state.manifest.target_options);
  fillSelect(elements.compareTargetSelect, state.manifest.target_options);
  fillSelect(elements.heteroMode, ["off", "on"], (value) => value === "off" ? "usa_2019" : "usa_2019 + Xc heterogeneity");
  fillSelect(elements.compareHeteroMode, ["off", "on"], (value) => value === "off" ? "usa_2019" : "usa_2019 + Xc heterogeneity");
  fillPresetSelect(elements.presetSelect);
  fillPresetSelect(elements.comparePresetSelect);
  fillAnalyticPresetSelect(elements.analyticPresetSelect);
  fillAnalyticPresetSelect(elements.compareAnalyticPresetSelect);

  elements.launchYear.value = `${state.manifest.default_launch_year}`;
  elements.projectionEndYear.value = `${state.manifest.default_projection_end_year}`;
  elements.branchSelect.value = state.manifest.default_branch;
  elements.compareBranchSelect.value = state.manifest.default_branch;
  elements.targetSelect.value = state.manifest.default_target;
  elements.compareTargetSelect.value = state.manifest.default_target;
  updateFactorOptions(elements.targetSelect, elements.factorSelect);
  updateFactorOptions(elements.compareTargetSelect, elements.compareFactorSelect, "1.00");
  syncFactorInput(elements.targetSelect, elements.factorInput);
  syncFactorInput(elements.compareTargetSelect, elements.compareFactorInput, "1.00");
  elements.heteroMode.value = "off";
  elements.compareHeteroMode.value = "off";
  elements.analyticPresetSelect.value = state.manifest.default_analytic_preset_id;
  elements.compareAnalyticPresetSelect.value = state.manifest.default_analytic_preset_id;
  elements.presetSelect.value = state.manifest.default_preset_id;
  elements.comparePresetSelect.value = state.manifest.default_compare_preset_id;
  applyPresetToActiveControls(elements.presetSelect.value);

  setControlsFromUrl();
  updateControlVisibility();
  refreshHelpText();
}


async function main() {
  try {
    await loadAssets();
    populateControls();
    connectHelpButtons();
    connectInputs();
    connectExports();
    await rerender();
    if (elements.pageShell) {
      elements.pageShell.dataset.ready = "true";
    }
  } catch (error) {
    console.error(error);
    setStatus("Load failed");
    showError(error.message || "Dashboard failed to load");
    if (elements.pageShell) {
      elements.pageShell.dataset.ready = "true";
    }
  }
}


main();
