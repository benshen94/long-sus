import {
  buildAgeDistributionSeries,
  buildHeatmap,
  buildLineSeries,
  normalizeDemography,
  buildPyramidSeries,
  projectScenario,
  rowsToCsv,
} from "./runtime.mjs?v=20260412f";
import { createInterventionStore } from "./interventions.mjs?v=20260412f";
import {
  describePreset,
  describeUptakeMode,
  explainScenarioStrategy,
  renderMethodsView,
} from "./content.mjs?v=20260412f";


const state = {
  manifest: null,
  activeArea: null,
  demography: null,
  analyticPresets: null,
  interventionStore: null,
  scenarioCatalog: [],
  activeResult: null,
  compareResult: null,
  renderToken: 0,
  fetchJson: null,
};


const elements = {
  pageShell: document.querySelector("[data-page-shell]"),
  mainViewToggle: document.getElementById("main-view-toggle"),
  loadStatus: document.getElementById("load-status"),
  loadError: document.getElementById("load-error"),
  areaSelect: document.getElementById("area-select"),
  areaViewToggle: document.getElementById("area-view-toggle"),
  areaMapPanel: document.getElementById("area-map-panel"),
  areaMap: document.getElementById("area-map"),
  areaListPanel: document.getElementById("area-list-panel"),
  areaList: document.getElementById("area-list"),
  presetField: document.getElementById("preset-field"),
  presetInfoToggle: document.getElementById("preset-info-toggle"),
  presetHelp: document.getElementById("preset-help"),
  uptakeModeInfoToggle: document.getElementById("uptake-mode-info-toggle"),
  uptakeModeHelp: document.getElementById("uptake-mode-help"),
  uptakeModeToggle: document.getElementById("uptake-mode-toggle"),
  presetSelect: document.getElementById("preset-select"),
  branchSelect: document.getElementById("branch-select"),
  targetInfoToggle: document.getElementById("target-info-toggle"),
  targetHelp: document.getElementById("target-help"),
  targetSelect: document.getElementById("target-select"),
  factorSelectField: document.getElementById("factor-select-field"),
  factorSelect: document.getElementById("factor-select"),
  factorInfoToggle: document.getElementById("factor-info-toggle"),
  factorHelp: document.getElementById("factor-help"),
  factorInputField: document.getElementById("factor-input-field"),
  factorInput: document.getElementById("factor-input"),
  heteroField: document.getElementById("hetero-field"),
  heteroMode: document.getElementById("hetero-mode"),
  analyticPresetField: document.getElementById("analytic-preset-field"),
  analyticPresetSelect: document.getElementById("analytic-preset-select"),
  launchYear: document.getElementById("launch-year"),
  projectionEndYear: document.getElementById("projection-end-year"),
  uptakeMode: document.getElementById("uptake-mode"),
  thresholdSettings: document.getElementById("threshold-settings"),
  thresholdField: document.getElementById("threshold-field"),
  thresholdAgeLabel: document.getElementById("threshold-age-label"),
  thresholdAge: document.getElementById("threshold-age"),
  thresholdProbabilityField: document.getElementById("threshold-probability-field"),
  thresholdProbability: document.getElementById("threshold-probability"),
  rolloutSettings: document.getElementById("rollout-settings"),
  rolloutCurveField: document.getElementById("rollout-curve-field"),
  rolloutCurve: document.getElementById("rollout-curve"),
  rolloutLaunchProbability: document.getElementById("rollout-launch-probability"),
  rolloutMaxProbability: document.getElementById("rollout-max-probability"),
  rolloutRampYearsField: document.getElementById("rollout-ramp-years-field"),
  rolloutRampYears: document.getElementById("rollout-ramp-years"),
  rolloutTakeoffYearsField: document.getElementById("rollout-takeoff-years-field"),
  rolloutTakeoffYears: document.getElementById("rollout-takeoff-years"),
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
  populationViewToggle: document.getElementById("population-view-toggle"),
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
  exportPyramidsCsv: document.getElementById("export-pyramids-csv"),
  exportSummaryCsv: document.getElementById("export-summary-csv"),
  exportsInfoToggle: document.getElementById("exports-info-toggle"),
  exportsHelp: document.getElementById("exports-help"),
  exportPyramidImage: document.getElementById("export-pyramid-image"),
  resetScenario: document.getElementById("reset-scenario"),
  resultsStage: document.getElementById("results-stage"),
  methodsStage: document.getElementById("methods-stage"),
};


const strategyButtons = elements.uptakeModeToggle
  ? [...elements.uptakeModeToggle.querySelectorAll("[data-uptake-mode]")]
  : [];

const populationViewButtons = elements.populationViewToggle
  ? [...elements.populationViewToggle.querySelectorAll("[data-population-view]")]
  : [];

const mainViewButtons = elements.mainViewToggle
  ? [...elements.mainViewToggle.querySelectorAll("[data-main-view]")]
  : [];

const areaViewButtons = elements.areaViewToggle
  ? [...elements.areaViewToggle.querySelectorAll("[data-area-view]")]
  : [];

const TARGET_LABELS = {
  eta: "slowing age (eta)",
  eta_shift: "rejuvenation (eta shift)",
  Xc: "increasing robustness (Xc)",
};

const TARGET_HELP = {
  eta: "Slowing age means the rate of aging, or damage production, is reduced after treatment starts.",
  eta_shift: "Rejuvenation means eta is shifted immediately after treatment starts. In this dashboard, eta_new = eta_old × factor.",
  Xc: "Increasing robustness means rectangularization of the survival curve: mortality stays lower until later ages, then rises more sharply.",
};

const ACTIVE_BANDED_TEMPLATE_IDS = [
  "only_elderly_65plus",
  "50pct_elderly_65plus",
  "30pct_middle_40_64_plus_70pct_elderly_65plus",
];


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


function formatSharePercent(value) {
  return `${Math.round(Number(value) * 100)}%`;
}


function targetLabel(target) {
  return TARGET_LABELS[target] || `${target}`;
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


function fillTargetSelect(select) {
  fillSelect(select, state.manifest.target_options, targetLabel);
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


function fillAreaSelect(select) {
  select.innerHTML = "";
  for (const area of state.manifest.areas || []) {
    const option = document.createElement("option");
    option.value = area.slug;
    option.textContent = area.country_label;
    select.append(option);
  }
}


function renderAreaList() {
  if (!elements.areaList) {
    return;
  }

  const grouped = new Map();
  for (const area of state.manifest.areas || []) {
    const continent = area.continent || "Other";
    if (!grouped.has(continent)) {
      grouped.set(continent, []);
    }
    grouped.get(continent).push(area);
  }

  const order = ["Global", "North America", "South America", "Europe", "Africa", "Asia", "Oceania", "Other"];
  const sections = [];

  for (const continent of order) {
    const areas = grouped.get(continent);
    if (!areas || areas.length === 0) {
      continue;
    }

    const buttons = areas
      .sort((left, right) => left.country_label.localeCompare(right.country_label))
      .map((area) => {
        const activeClass = state.activeArea?.slug === area.slug ? " is-active" : "";
        return `<button type="button" class="area-chip${activeClass}" data-area-slug="${area.slug}">${area.country_label}</button>`;
      })
      .join("");

    sections.push(`
      <section class="area-group">
        <p class="area-group-title">${continent}</p>
        <div class="area-button-grid">${buttons}</div>
      </section>
    `);
  }

  elements.areaList.innerHTML = sections.join("");
  for (const button of elements.areaList.querySelectorAll("[data-area-slug]")) {
    button.addEventListener("click", async () => {
      const areaSlug = button.dataset.areaSlug;
      if (!areaSlug || areaSlug === state.activeArea?.slug) {
        return;
      }
      await selectArea(areaSlug);
    });
  }
}


function renderAreaMap() {
  if (!elements.areaMap) {
    return;
  }

  const areas = (state.manifest.areas || []).filter((area) => area.iso3 && area.iso3 !== "OWID_WRL");
  const locations = areas.map((area) => area.iso3);
  const values = areas.map((area) => area.slug === state.activeArea?.slug ? 2 : 1);
  const names = areas.map((area) => area.country_label);

  Plotly.react(elements.areaMap, [{
    type: "choropleth",
    locationmode: "ISO-3",
    locations,
    z: values,
    text: names,
    customdata: areas.map((area) => area.slug),
    hovertemplate: "%{text}<br>Click to select<extra></extra>",
    colorscale: [
      [0.0, "#d8cfbf"],
      [0.499, "#d8cfbf"],
      [0.5, "#d35f3d"],
      [1.0, "#d35f3d"],
    ],
    zmin: 1,
    zmax: 2,
    showscale: false,
    marker: {
      line: { color: "rgba(90, 80, 65, 0.45)", width: 0.5 },
    },
  }], {
    margin: { l: 0, r: 0, t: 0, b: 0 },
    paper_bgcolor: "rgba(0,0,0,0)",
    geo: {
      scope: "world",
      projection: { type: "natural earth" },
      showframe: false,
      showcoastlines: false,
      showcountries: true,
      countrycolor: "rgba(90, 80, 65, 0.25)",
      bgcolor: "rgba(0,0,0,0)",
      landcolor: "#f4ede1",
      oceancolor: "#eef3f0",
      showocean: true,
    },
  }, { responsive: true, displayModeBar: false });

  if (elements.areaMap.__areaClickBound) {
    return;
  }

  elements.areaMap.__areaClickBound = true;
  elements.areaMap.on("plotly_click", async (event) => {
    const point = event?.points?.[0];
    const areaSlug = point?.customdata;
    if (!areaSlug || areaSlug === state.activeArea?.slug) {
      return;
    }
    await selectArea(areaSlug);
  });
}


function renderAreaSelector() {
  renderAreaMap();
  renderAreaList();
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


function findArea(areaSlug) {
  const safeSlug = areaSlug || state.manifest.default_area;
  const area = (state.manifest.areas || []).find((entry) => entry.slug === safeSlug);
  if (!area) {
    throw new Error(`Unknown area: ${safeSlug}`);
  }
  return area;
}


function currentCountryLabel() {
  return state.activeArea?.country_label || state.manifest.country_label || state.manifest.country;
}


function currentCountryName() {
  return state.activeArea?.country || state.manifest.country;
}


function defaultFactorForTarget(target) {
  if (target === "eta_shift") {
    return Number(state.manifest.default_eta_shift_factor || 1.2);
  }
  if (target === "Xc") {
    return Number(state.manifest.default_xc_factor);
  }
  return Number(state.manifest.default_eta_factor);
}


function analyticFactorMin() {
  return Number(state.manifest.analytic_factor_min || 0.5);
}


function analyticFactorMax() {
  return Number(state.manifest.analytic_factor_max || 1.5);
}


function analyticFactorStep() {
  return Number(state.manifest.analytic_factor_step || 0.01);
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


function normalizeRolloutCurve(value) {
  if (value === "logistic") {
    return "logistic";
  }
  return "linear";
}


function currentRolloutLaunchProbability() {
  const parsed = Number(elements.rolloutLaunchProbability.value);
  if (!Number.isFinite(parsed)) {
    const fallback = Number(state.manifest.default_rollout_launch_probability || 10);
    elements.rolloutLaunchProbability.value = `${fallback}`;
    return fallback / 100;
  }

  const clamped = Math.max(0, Math.min(100, parsed));
  elements.rolloutLaunchProbability.value = `${Math.round(clamped)}`;
  return clamped / 100;
}


function currentRolloutMaxProbability(launchProbability = currentRolloutLaunchProbability()) {
  const parsed = Number(elements.rolloutMaxProbability.value);
  if (!Number.isFinite(parsed)) {
    const fallback = Number(state.manifest.default_rollout_max_probability || 50);
    elements.rolloutMaxProbability.value = `${fallback}`;
    return fallback / 100;
  }

  const clamped = Math.max(launchProbability * 100, Math.min(100, parsed));
  elements.rolloutMaxProbability.value = `${Math.round(clamped)}`;
  return clamped / 100;
}


function currentRolloutYears(input, fallback) {
  const parsed = Number(input.value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    input.value = `${fallback}`;
    return fallback;
  }

  const rounded = Math.max(1, Math.round(parsed));
  input.value = `${rounded}`;
  return rounded;
}


function refreshHelpText() {
  if (elements.presetHelp) {
    if (elements.uptakeMode.value !== "banded") {
      elements.presetHelp.textContent = "";
    } else {
      const preset = findPreset(elements.presetSelect.value);
      elements.presetHelp.textContent = `${describePreset(preset)} Templates are starting points only. You can edit the band shares and start rule below.`;
    }
  }
  if (elements.uptakeModeHelp) {
    elements.uptakeModeHelp.textContent = describeUptakeMode(elements.uptakeMode.value);
  }
  if (elements.targetHelp) {
    const target = elements.targetSelect.value;
    elements.targetHelp.textContent = TARGET_HELP[target] || "";
  }
  if (elements.factorHelp) {
    const target = elements.targetSelect.value;
    if (target === "eta") {
      elements.factorHelp.textContent = "Factor multiplies eta after treatment starts. Smaller values mean slower aging.";
    } else if (target === "eta_shift") {
      elements.factorHelp.textContent = "Factor multiplies eta directly: eta_new = eta_old × factor. Larger values mean a larger immediate rejuvenation-style shift.";
    } else if (target === "Xc") {
      elements.factorHelp.textContent = "Factor multiplies Xc after treatment starts. Larger values mean stronger robustness and more rectangular survival.";
    } else {
      elements.factorHelp.textContent = "";
    }
  }
  if (elements.exportsHelp) {
    elements.exportsHelp.textContent = "Detailed population CSV exports one row per year, sex, and age, with treated and untreated counts. All-years age CSV exports a compact age-by-year table that is easier to reuse for pyramids. Summary CSV exports one row per year with total population, treated share, births, deaths, median age, and old-age shares. Export current view saves the active chart as a PNG.";
  }
}


function presetOptionsForMode(mode) {
  if (mode !== "banded") {
    return [];
  }

  return state.scenarioCatalog.filter((preset) => ACTIVE_BANDED_TEMPLATE_IDS.includes(preset.id));
}


function defaultPresetIdForMode(mode) {
  if (mode === "banded") {
    return "30pct_middle_40_64_plus_70pct_elderly_65plus";
  }
  return "";
}


function renderActivePresetOptions(mode, selectedId = null) {
  const options = presetOptionsForMode(mode);
  elements.presetSelect.innerHTML = "";

  if (mode !== "banded") {
    return;
  }

  for (const preset of options) {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.label;
    elements.presetSelect.append(option);
  }

  const optionIds = options.map((preset) => preset.id);
  const defaultId = defaultPresetIdForMode(mode);
  const fallbackId = optionIds.includes(defaultId) ? defaultId : optionIds[0];
  const nextSelectedId = selectedId && optionIds.includes(selectedId)
    ? selectedId
    : fallbackId;

  if (nextSelectedId) {
    elements.presetSelect.value = nextSelectedId;
  }
}


function syncUptakeModeToggle() {
  for (const button of strategyButtons) {
    const isActive = button.dataset.uptakeMode === elements.uptakeMode.value;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", `${isActive}`);
  }
}


function currentPopulationView() {
  const activeButton = populationViewButtons.find((button) => button.classList.contains("is-active"));
  if (!activeButton) {
    return "distribution";
  }
  return activeButton.dataset.populationView || "distribution";
}


function syncPopulationViewToggle(nextView) {
  const safeView = ["distribution", "pyramid"].includes(nextView) ? nextView : "distribution";
  for (const button of populationViewButtons) {
    const isActive = button.dataset.populationView === safeView;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", `${isActive}`);
  }
}


function currentMainView() {
  const activeButton = mainViewButtons.find((button) => button.classList.contains("is-active"));
  if (!activeButton) {
    return "results";
  }
  return activeButton.dataset.mainView || "results";
}


function syncMainViewToggle(nextView) {
  const safeView = ["results", "methods"].includes(nextView) ? nextView : "results";
  for (const button of mainViewButtons) {
    const isActive = button.dataset.mainView === safeView;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", `${isActive}`);
    button.setAttribute("aria-selected", `${isActive}`);
    button.setAttribute("tabindex", isActive ? "0" : "-1");
  }

  if (elements.resultsStage) {
    elements.resultsStage.hidden = safeView !== "results";
  }
  if (elements.methodsStage) {
    elements.methodsStage.hidden = safeView !== "methods";
  }
}


function currentAreaView() {
  const activeButton = areaViewButtons.find((button) => button.classList.contains("is-active"));
  if (!activeButton) {
    return "map";
  }
  return activeButton.dataset.areaView || "map";
}


function defaultAreaView() {
  if (window.matchMedia("(max-width: 720px)").matches) {
    return "list";
  }
  return "map";
}


function syncAreaViewToggle(nextView) {
  const safeView = ["map", "list"].includes(nextView) ? nextView : "map";
  for (const button of areaViewButtons) {
    const isActive = button.dataset.areaView === safeView;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-pressed", `${isActive}`);
  }

  if (elements.areaMapPanel) {
    elements.areaMapPanel.hidden = safeView !== "map";
  }
  if (elements.areaListPanel) {
    elements.areaListPanel.hidden = safeView !== "list";
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
    [elements.targetInfoToggle, elements.targetHelp],
    [elements.factorInfoToggle, elements.factorHelp],
    [elements.exportsInfoToggle, elements.exportsHelp],
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


function currentThresholdProbability() {
  const parsed = Number(elements.thresholdProbability.value);
  if (!Number.isFinite(parsed)) {
    elements.thresholdProbability.value = "100";
    return 1.0;
  }

  const clamped = Math.max(0, Math.min(100, parsed));
  elements.thresholdProbability.value = `${Math.round(clamped)}`;
  return clamped / 100;
}


function applyPresetToActiveControls(presetId) {
  const preset = findPreset(presetId);
  if (preset.uptake_mode !== "banded") {
    return;
  }

  renderActivePresetOptions("banded", preset.id);
  elements.startRule.value = normalizeBandedStartRule(preset.start_rule_within_band);

  const bands = preset.bands || state.manifest.default_bands;
  elements.band2039.value = "0";
  elements.band4064.value = "0";
  elements.band65Plus.value = "0";

  for (const band of bands) {
    const shareText = `${Math.round(Number(band.target_share) * 100)}`;
    if (Number(band.start_age) === 20 && Number(band.end_age) === 39) {
      elements.band2039.value = shareText;
      continue;
    }
    if (Number(band.start_age) === 40 && Number(band.end_age) === 64) {
      elements.band4064.value = shareText;
      continue;
    }
    if (Number(band.start_age) === 65 && (band.end_age === null || band.end_age === undefined)) {
      elements.band65Plus.value = shareText;
    }
  }

  refreshHelpText();
}


function updateFactorOptions(targetSelect, factorSelect, selectedValue = null) {
  const target = targetSelect.value;
  const isCompare = factorSelect === elements.compareFactorSelect;
  const branch = isCompare ? elements.compareBranchSelect.value : elements.branchSelect.value;
  const branchFactorGrids = state.manifest.branch_factor_grids || {};
  const branchGrid = branchFactorGrids[branch] || {};
  const factorGrid = branchGrid[target] || state.manifest.factor_grids[target];
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
  if (Number.isFinite(parsed)) {
    const clamped = Math.min(analyticFactorMax(), Math.max(analyticFactorMin(), parsed));
    input.value = clamped.toFixed(2);
    return clamped;
  }

  const fallback = defaultFactorForTarget(target);
  input.value = fallback.toFixed(2);
  return fallback;
}


function configureFactorInput(input) {
  input.min = analyticFactorMin().toFixed(2);
  input.max = analyticFactorMax().toFixed(2);
  input.step = analyticFactorStep().toFixed(2);
}


function currentYear() {
  return Number(elements.yearSlider.value);
}


function buildScenarioName({
  schemeId,
  target,
  factor,
  branch,
  heteroMode,
  analyticPresetId,
  uptakeMode,
  thresholdAge,
  thresholdProbability,
  rolloutCurve,
  rolloutLaunchProbability,
  rolloutMaxProbability,
  rolloutRampYears,
  rolloutTakeoffYears,
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

  let strategyKey = schemeId;
  if (uptakeMode === "threshold") {
    strategyKey = `threshold_age_${thresholdAge}_share_${Math.round(Number(thresholdProbability) * 100)}`;
  } else if (uptakeMode === "rollout") {
    const launchText = Math.round(Number(rolloutLaunchProbability) * 100);
    const maxText = Math.round(Number(rolloutMaxProbability) * 100);
    if (rolloutCurve === "logistic") {
      strategyKey = `rollout_age_${thresholdAge}_logistic_launch_${launchText}_cap_${maxText}_takeoff_${rolloutTakeoffYears}`;
    } else {
      strategyKey = `rollout_age_${thresholdAge}_linear_launch_${launchText}_cap_${maxText}_ramp_${rolloutRampYears}`;
    }
  }

  const factorText = Number(factor).toFixed(2);
  if (branch === "analytic_arm") {
    return `${strategyKey}_${branch}_${analyticPresetId}_${target}_${factorText}x`;
  }

  const heteroSuffix = heteroMode === "on" ? "_hetero" : "";
  return `${strategyKey}_${target}_${factorText}x${heteroSuffix}`;
}


function buildActiveScenario() {
  const branch = state.manifest.default_branch;
  const target = elements.targetSelect.value;
  const factor = branch === "analytic_arm"
    ? numericFactorValue(elements.factorInput, elements.targetSelect.value)
    : Number(elements.factorSelect.value);
  const heteroMode = branch === "sr" ? elements.heteroMode.value : "off";
  const analyticPresetId = branch === "analytic_arm" ? elements.analyticPresetSelect.value : null;
  const uptakeMode = elements.uptakeMode.value;
  const thresholdAge = uptakeMode === "banded" ? null : Number(elements.thresholdAge.value);
  const thresholdProbability = uptakeMode === "threshold" ? currentThresholdProbability() : 1.0;
  const rolloutCurve = uptakeMode === "rollout" ? normalizeRolloutCurve(elements.rolloutCurve.value) : "linear";
  const rolloutLaunchProbability = uptakeMode === "rollout" ? currentRolloutLaunchProbability() : 0.10;
  const rolloutMaxProbability = uptakeMode === "rollout"
    ? currentRolloutMaxProbability(rolloutLaunchProbability)
    : 0.50;
  const rolloutRampYears = uptakeMode === "rollout"
    ? currentRolloutYears(elements.rolloutRampYears, Number(state.manifest.default_rollout_ramp_years || 12))
    : Number(state.manifest.default_rollout_ramp_years || 12);
  const rolloutTakeoffYears = uptakeMode === "rollout"
    ? currentRolloutYears(elements.rolloutTakeoffYears, Number(state.manifest.default_rollout_takeoff_years || 8))
    : Number(state.manifest.default_rollout_takeoff_years || 8);
  const bands = uptakeMode === "banded" ? buildBandsFromInputs() : [];
  const startRule = uptakeMode === "banded"
    ? normalizeBandedStartRule(elements.startRule.value)
    : "deterministic_threshold";
  const schemeId = uptakeMode === "threshold"
    ? "custom_threshold"
    : uptakeMode === "rollout"
      ? `custom_rollout_${rolloutCurve}`
      : elements.presetSelect.value;
  const label = uptakeMode === "threshold"
    ? `Threshold age ${thresholdAge}, ${formatSharePercent(thresholdProbability)} take-up`
    : uptakeMode === "rollout"
      ? `Rollout age ${thresholdAge}, ${rolloutCurve === "logistic" ? "logistic" : "linear"} curve`
      : findPreset(elements.presetSelect.value).label;

  return {
    name: buildScenarioName({
      schemeId,
      target,
      factor,
      branch,
      heteroMode,
      analyticPresetId,
      uptakeMode,
      thresholdAge,
      thresholdProbability,
      rolloutCurve,
      rolloutLaunchProbability,
      rolloutMaxProbability,
      rolloutRampYears,
      rolloutTakeoffYears,
    }),
    label,
    scheme_id: schemeId,
    country: currentCountryName(),
    mode: "dynamic",
    launch_year: Number(elements.launchYear.value),
    projection_end_year: Number(elements.projectionEndYear.value),
    uptake_mode: uptakeMode,
    threshold_age: thresholdAge,
    threshold_probability: thresholdProbability,
    bands,
    start_rule_within_band: startRule,
    rollout_curve: rolloutCurve,
    rollout_launch_probability: rolloutLaunchProbability,
    rollout_max_probability: rolloutMaxProbability,
    rollout_ramp_years: rolloutRampYears,
    rollout_takeoff_years: rolloutTakeoffYears,
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
  const thresholdProbability = Number(preset.threshold_probability ?? 1.0);
  const rolloutCurve = normalizeRolloutCurve(preset.rollout_curve || state.manifest.default_rollout_curve);
  const rolloutLaunchProbability = Number(
    preset.rollout_launch_probability ?? (Number(state.manifest.default_rollout_launch_probability || 10) / 100),
  );
  const rolloutMaxProbability = Number(
    preset.rollout_max_probability ?? (Number(state.manifest.default_rollout_max_probability || 50) / 100),
  );
  const rolloutRampYears = Number(
    preset.rollout_ramp_years ?? state.manifest.default_rollout_ramp_years ?? 12,
  );
  const rolloutTakeoffYears = Number(
    preset.rollout_takeoff_years ?? state.manifest.default_rollout_takeoff_years ?? 8,
  );

  return {
    name: buildScenarioName({
      schemeId: preset.id,
      target,
      factor,
      branch,
      heteroMode,
      analyticPresetId,
      uptakeMode: preset.uptake_mode,
      thresholdAge: preset.threshold_age,
      thresholdProbability,
      rolloutCurve,
      rolloutLaunchProbability,
      rolloutMaxProbability,
      rolloutRampYears,
      rolloutTakeoffYears,
    }),
    label: preset.label,
    scheme_id: preset.id,
    country: currentCountryName(),
    mode: "dynamic",
    launch_year: Number(elements.launchYear.value),
    projection_end_year: Number(elements.projectionEndYear.value),
    uptake_mode: preset.uptake_mode,
    threshold_age: preset.threshold_age,
    threshold_probability: thresholdProbability,
    bands: preset.bands || [],
    start_rule_within_band: compareStartRule,
    rollout_curve: rolloutCurve,
    rollout_launch_probability: rolloutLaunchProbability,
    rollout_max_probability: rolloutMaxProbability,
    rollout_ramp_years: rolloutRampYears,
    rollout_takeoff_years: rolloutTakeoffYears,
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
  const comparePreset = findPreset(elements.comparePresetSelect.value);
  const activeBranch = state.manifest.default_branch;
  const compareBranch = state.manifest.default_branch;
  const compareIsBaseline = comparePreset.id === "no_one";
  const uptakeMode = elements.uptakeMode.value;
  const thresholdProbability = currentThresholdProbability();
  const rolloutCurve = normalizeRolloutCurve(elements.rolloutCurve.value);
  const rolloutLaunchProbability = currentRolloutLaunchProbability();
  const rolloutMaxProbability = currentRolloutMaxProbability(rolloutLaunchProbability);

  elements.targetSelect.disabled = false;
  elements.factorSelect.disabled = true;
  elements.factorInput.disabled = false;
  elements.heteroMode.disabled = true;
  elements.analyticPresetSelect.disabled = elements.analyticPresetSelect.options.length <= 1;
  elements.uptakeMode.disabled = false;

  elements.factorSelectField.hidden = true;
  elements.factorInputField.hidden = false;
  elements.heteroField.hidden = true;
  elements.analyticPresetField.hidden = elements.analyticPresetSelect.options.length <= 1;

  elements.presetField.hidden = uptakeMode !== "banded";
  elements.thresholdSettings.hidden = uptakeMode === "banded";
  elements.thresholdField.hidden = uptakeMode === "banded";
  elements.thresholdProbabilityField.hidden = uptakeMode !== "threshold";
  elements.rolloutSettings.hidden = uptakeMode !== "rollout";
  elements.rolloutCurveField.hidden = uptakeMode !== "rollout";
  elements.rolloutRampYearsField.hidden = uptakeMode !== "rollout" || rolloutCurve !== "linear";
  elements.rolloutTakeoffYearsField.hidden = uptakeMode !== "rollout" || rolloutCurve !== "logistic";
  elements.startRuleField.hidden = uptakeMode !== "banded";
  elements.bandEditor.hidden = uptakeMode !== "banded";
  if (elements.thresholdAgeLabel) {
    elements.thresholdAgeLabel.textContent = uptakeMode === "rollout" ? "Eligibility age" : "Threshold age";
  }

  elements.compareTargetSelect.disabled = compareIsBaseline;
  elements.compareFactorSelect.disabled = true;
  elements.compareFactorInput.disabled = compareIsBaseline;
  elements.compareHeteroMode.disabled = true;
  elements.compareAnalyticPresetSelect.disabled = elements.compareAnalyticPresetSelect.options.length <= 1;

  elements.compareFactorSelectField.hidden = true;
  elements.compareFactorInputField.hidden = false;
  elements.compareHeteroField.hidden = true;
  elements.compareAnalyticPresetField.hidden = elements.compareAnalyticPresetSelect.options.length <= 1;

  elements.schemeExplainer.textContent = `${explainScenarioStrategy(buildActiveScenario())} Branch: ${branchLabel(activeBranch)}.`;

  if (compareIsBaseline) {
    elements.compareExplainer.textContent = `Comparison scenario is the untreated baseline on the ${branchLabel(compareBranch)} branch.`;
  } else {
    elements.compareExplainer.textContent = `${explainScenarioStrategy(buildCompareScenario())} Branch: ${branchLabel(compareBranch)}.`;
  }
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
  const maxAge = state.demography.ages[state.demography.ages.length - 1];
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
    margin: { l: 60, r: 30, t: 54, b: 108 },
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
      range: [0, maxAge],
      dtick: 20,
    },
    legend: {
      orientation: "h",
      x: 0.5,
      xanchor: "center",
      y: -0.28,
      yanchor: "top",
      bgcolor: "rgba(0,0,0,0)",
    },
    transition: { duration: 220, easing: "cubic-out" },
  }, { responsive: true, displayModeBar: false });
}


function renderAgeDistribution(plotElement, result, year, titleText, palette) {
  if (!plotElement) {
    return;
  }

  const series = buildAgeDistributionSeries(result, year);
  const maxAge = state.demography.ages[state.demography.ages.length - 1];

  Plotly.react(plotElement, [
    {
      type: "bar",
      x: series.ages,
      y: series.untreated.map((value) => value / 1_000_000),
      marker: { color: palette.untreated },
      name: "Untreated",
    },
    {
      type: "bar",
      x: series.ages,
      y: series.treated.map((value) => value / 1_000_000),
      marker: { color: palette.treated },
      name: "Treated",
    },
  ], {
    title: { text: titleText, font: { family: "Instrument Serif", size: 24 } },
    barmode: "stack",
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    margin: { l: 68, r: 24, t: 54, b: 112 },
    xaxis: {
      title: "Age",
      gridcolor: "#ece4d7",
      range: [0, maxAge],
      dtick: 20,
    },
    yaxis: {
      title: "Population (millions)",
      gridcolor: "#d7d0c2",
    },
    legend: {
      orientation: "h",
      x: 0.5,
      xanchor: "center",
      y: -0.3,
      yanchor: "top",
      bgcolor: "rgba(0,0,0,0)",
    },
    transition: { duration: 220, easing: "cubic-out" },
  }, { responsive: true, displayModeBar: false });
}


function renderPopulationChart(plotElement, result, year, titleText, palette) {
  if (currentPopulationView() === "pyramid") {
    renderPyramid(plotElement, result, year, titleText);
    return;
  }

  renderAgeDistribution(plotElement, result, year, titleText, palette);
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
    margin: { l: 56, r: 20, t: 48, b: 98 },
    xaxis: { title: "Year", gridcolor: "#ece4d7" },
    yaxis: { title: "Millions", gridcolor: "#d7d0c2" },
    legend: { orientation: "h", x: 0.5, xanchor: "center", y: -0.28, yanchor: "top", bgcolor: "rgba(0,0,0,0)" },
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
    margin: { l: 56, r: 20, t: 48, b: 98 },
    xaxis: { title: "Year", gridcolor: "#ece4d7" },
    yaxis: { title: "Percent", gridcolor: "#d7d0c2" },
    legend: { orientation: "h", x: 0.5, xanchor: "center", y: -0.28, yanchor: "top", bgcolor: "rgba(0,0,0,0)" },
  }, { responsive: true, displayModeBar: false });
}


function relevantScenarioMaxAge(scenario) {
  if (scenario.uptake_mode === "threshold" || scenario.uptake_mode === "rollout") {
    return Number(scenario.threshold_age ?? 0);
  }

  let maxConfiguredAge = 0;
  for (const band of scenario.bands || []) {
    const bandEdge = band.end_age === null || band.end_age === undefined
      ? band.start_age
      : band.end_age;
    maxConfiguredAge = Math.max(maxConfiguredAge, Number(bandEdge));
  }
  return maxConfiguredAge;
}


function heatmapDisplayMaxAge(scenario) {
  const maxAge = state.demography.ages[state.demography.ages.length - 1];
  const relevantAge = relevantScenarioMaxAge(scenario);
  return Math.min(maxAge, Math.max(120, relevantAge + 25));
}


function renderHeatmap(activeScenario) {
  if (!elements.treatedHeatmapChart) {
    return;
  }

  const heatmap = buildHeatmap(state.activeResult);
  const maxDisplayAge = heatmapDisplayMaxAge(activeScenario);
  const visibleAgeIndexes = heatmap.ages
    .map((age, index) => ({ age, index }))
    .filter(({ age }) => age <= maxDisplayAge)
    .map(({ index }) => index);
  const visibleAges = visibleAgeIndexes.map((index) => heatmap.ages[index]);
  const visibleValues = visibleAgeIndexes.map((index) => heatmap.values[index]);

  Plotly.react(elements.treatedHeatmapChart, [{
    z: visibleValues,
    x: heatmap.years,
    y: visibleAges,
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
    yaxis: { title: "Age", range: [0, maxDisplayAge], dtick: 20 },
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
    margin: { l: 56, r: 20, t: 48, b: 98 },
    xaxis: { title: "Age", gridcolor: "#ece4d7" },
    yaxis: { title: "People alive per 1000", gridcolor: "#d7d0c2" },
    legend: { orientation: "h", x: 0.5, xanchor: "center", y: -0.28, yanchor: "top", bgcolor: "rgba(0,0,0,0)" },
  }, { responsive: true, displayModeBar: false });
}


function scenarioHeadline(scenario) {
  const branchText = branchLabel(scenario.branch);
  if (scenario.target === null) {
    return `${scenario.label} | ${branchText} | launch ${scenario.launch_year}`;
  }

  if (scenario.branch === "analytic_arm") {
    const preset = findAnalyticPreset(scenario.analytic_preset_id);
    return `${scenario.label} | ${branchText} ${preset.label} | ${targetLabel(scenario.target)} ${formatFactor(scenario.factor)} | launch ${scenario.launch_year}`;
  }

  return `${scenario.label} | ${branchText} ${targetLabel(scenario.target)} ${formatFactor(scenario.factor)} | launch ${scenario.launch_year}`;
}


function renderScenarioLabels(activeScenario, compareScenario) {
  if (elements.activeScenarioLabel) {
    elements.activeScenarioLabel.textContent = scenarioHeadline(activeScenario);
  }
  if (elements.compareScenarioLabel) {
    elements.compareScenarioLabel.textContent = scenarioHeadline(compareScenario);
  }
}


function renderMethodsStage(activeScenario) {
  const analyticPreset = findAnalyticPreset(activeScenario.analytic_preset_id);
  renderMethodsView(elements.methodsStage, {
    countryLabel: currentCountryLabel(),
    analyticPresetLabel: analyticPreset.label,
    activeScenario,
    activeSummary: activeSummaryRow(),
  });
}


function updateUrl(activeScenario, compareScenario, selectedYear) {
  const params = new URLSearchParams();
  params.set("area", state.activeArea?.slug || state.manifest.default_area);
  if (activeScenario.uptake_mode === "banded") {
    params.set("preset", activeScenario.scheme_id);
  }
  params.set("mainView", currentMainView());
  params.set("branch", activeScenario.branch);
  params.set("target", activeScenario.target || "none");
  params.set("factor", activeScenario.factor.toFixed(2));
  params.set("hetero", activeScenario.hetero_mode);
  params.set("analyticPreset", activeScenario.analytic_preset_id || "");
  params.set("launch", `${activeScenario.launch_year}`);
  params.set("end", `${activeScenario.projection_end_year}`);
  params.set("uptake", activeScenario.uptake_mode);
  params.set("threshold", `${activeScenario.threshold_age ?? -1}`);
  params.set("thresholdProbability", `${Math.round(Number(activeScenario.threshold_probability ?? 1.0) * 100)}`);
  params.set("startRule", activeScenario.start_rule_within_band);
  params.set("rolloutCurve", activeScenario.rollout_curve);
  params.set("rolloutLaunchProbability", `${Math.round(Number(activeScenario.rollout_launch_probability ?? 0) * 100)}`);
  params.set("rolloutMaxProbability", `${Math.round(Number(activeScenario.rollout_max_probability ?? 0) * 100)}`);
  params.set("rolloutRampYears", `${activeScenario.rollout_ramp_years ?? 0}`);
  params.set("rolloutTakeoffYears", `${activeScenario.rollout_takeoff_years ?? 0}`);
  params.set("band2039", elements.band2039.value);
  params.set("band4064", elements.band4064.value);
  params.set("band65", elements.band65Plus.value);
  params.set("comparePreset", compareScenario.scheme_id);
  params.set("compareBranch", compareScenario.branch);
  params.set("compareTarget", compareScenario.target || "none");
  params.set("compareFactor", compareScenario.factor.toFixed(2));
  params.set("compareHetero", compareScenario.hetero_mode);
  params.set("compareAnalyticPreset", compareScenario.analytic_preset_id || "");
  params.set("areaView", currentAreaView());
  params.set("populationView", currentPopulationView());
  params.set("year", `${selectedYear}`);
  history.replaceState(null, "", `?${params.toString()}`);
}


function setControlsFromUrl() {
  const params = new URLSearchParams(window.location.search);

  if (params.has("area")) {
    elements.areaSelect.value = params.get("area");
  }
  if (params.has("mainView")) {
    syncMainViewToggle(params.get("mainView"));
  }
  if (params.has("areaView")) {
    syncAreaViewToggle(params.get("areaView"));
  }

  if (params.has("uptake")) {
    elements.uptakeMode.value = params.get("uptake");
    renderActivePresetOptions(elements.uptakeMode.value, elements.presetSelect.value);
    syncUptakeModeToggle();
  }

  if (params.has("preset") && elements.uptakeMode.value === "banded") {
    applyPresetToActiveControls(params.get("preset"));
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
  if (params.has("threshold")) {
    elements.thresholdAge.value = params.get("threshold");
  }
  if (params.has("thresholdProbability")) {
    elements.thresholdProbability.value = params.get("thresholdProbability");
  }
  if (params.has("rolloutCurve")) {
    elements.rolloutCurve.value = normalizeRolloutCurve(params.get("rolloutCurve"));
  }
  if (params.has("rolloutLaunchProbability")) {
    elements.rolloutLaunchProbability.value = params.get("rolloutLaunchProbability");
  }
  if (params.has("rolloutMaxProbability")) {
    elements.rolloutMaxProbability.value = params.get("rolloutMaxProbability");
  }
  if (params.has("rolloutRampYears")) {
    elements.rolloutRampYears.value = params.get("rolloutRampYears");
  }
  if (params.has("rolloutTakeoffYears")) {
    elements.rolloutTakeoffYears.value = params.get("rolloutTakeoffYears");
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
  if (params.has("populationView")) {
    syncPopulationViewToggle(params.get("populationView"));
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
  renderPopulationChart(
    elements.pyramidChart,
    state.activeResult,
    selectedYear,
    `Active scenario · ${selectedYear}`,
    { untreated: "#aeb8cf", treated: "#16314d" },
  );
  renderPopulationChart(
    elements.comparePyramidChart,
    state.compareResult,
    selectedYear,
    `Comparison scenario · ${selectedYear}`,
    { untreated: "#f0b29f", treated: "#8e2f21" },
  );
  renderLineCharts();
  renderHeatmap(activeScenario);
  renderSurvivalChart();
  renderMethodsStage(activeScenario);
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


function captureControlState() {
  return {
    area: elements.areaSelect?.value || state.activeArea?.slug || state.manifest.default_area,
    mainView: currentMainView(),
    preset: elements.presetSelect.value,
    comparePreset: elements.comparePresetSelect.value,
    target: elements.targetSelect.value,
    compareTarget: elements.compareTargetSelect.value,
    factor: elements.factorInput.value,
    compareFactor: elements.compareFactorInput.value,
    launchYear: elements.launchYear.value,
    projectionEndYear: elements.projectionEndYear.value,
    thresholdAge: elements.thresholdAge.value,
    thresholdProbability: elements.thresholdProbability.value,
    rolloutCurve: elements.rolloutCurve.value,
    rolloutLaunchProbability: elements.rolloutLaunchProbability.value,
    rolloutMaxProbability: elements.rolloutMaxProbability.value,
    rolloutRampYears: elements.rolloutRampYears.value,
    rolloutTakeoffYears: elements.rolloutTakeoffYears.value,
    startRule: elements.startRule.value,
    band2039: elements.band2039.value,
    band4064: elements.band4064.value,
    band65Plus: elements.band65Plus.value,
    uptakeMode: elements.uptakeMode.value,
    analyticPreset: elements.analyticPresetSelect.value,
    compareAnalyticPreset: elements.compareAnalyticPresetSelect.value,
    areaView: currentAreaView(),
    populationView: currentPopulationView(),
  };
}


function applyAreaMetadata(area) {
  state.activeArea = area;
  state.manifest.country = area.country;
  state.manifest.country_label = area.country_label;
  state.manifest.default_analytic_preset_id = area.default_analytic_preset_id;
  state.manifest.paths.demography = area.paths.demography;
  state.manifest.paths.analytic_presets = area.paths.analytic_presets;
  state.manifest.paths.calibration = area.paths.calibration;
  document.title = `${area.country_label} Analytic Longevity Dashboard`;
}


async function loadAreaAssets(areaSlug) {
  const area = findArea(areaSlug);
  applyAreaMetadata(area);

  const [demography, analyticPresets] = await Promise.all([
    state.fetchJson(area.paths.demography),
    state.fetchJson(area.paths.analytic_presets),
  ]);

  state.demography = normalizeDemography(demography);
  state.analyticPresets = analyticPresets;
  state.interventionStore = createInterventionStore({
    manifest: state.manifest,
    demography: state.demography,
    analyticPresets: state.analyticPresets,
    fetchJson: state.fetchJson,
  });
}


async function selectArea(areaSlug) {
  if (!areaSlug) {
    return;
  }

  elements.areaSelect.value = areaSlug;
  await loadAreaAssets(areaSlug);
  populateControls({ preserveSelections: true });
  renderAreaSelector();
  await rerender();
}


function buildAllYearsPyramidRows(result) {
  const rows = [];
  const years = Object.keys(result.snapshots)
    .map((value) => Number(value))
    .sort((a, b) => a - b);

  for (const year of years) {
    const snapshot = result.snapshots[String(year)];
    for (let age = 0; age < snapshot.untreated.male.length; age += 1) {
      const maleUntreated = snapshot.untreated.male[age];
      const femaleUntreated = snapshot.untreated.female[age];
      const maleTreated = snapshot.treatedByAge.male[age];
      const femaleTreated = snapshot.treatedByAge.female[age];

      rows.push({
        year,
        age,
        male_total: maleUntreated + maleTreated,
        female_total: femaleUntreated + femaleTreated,
        male_treated: maleTreated,
        female_treated: femaleTreated,
        male_untreated: maleUntreated,
        female_untreated: femaleUntreated,
        total_population: maleUntreated + maleTreated + femaleUntreated + femaleTreated,
        total_treated: maleTreated + femaleTreated,
        total_untreated: maleUntreated + femaleUntreated,
        treated_share: maleUntreated + maleTreated + femaleUntreated + femaleTreated > 0
          ? (maleTreated + femaleTreated) / (maleUntreated + maleTreated + femaleUntreated + femaleTreated)
          : 0,
      });
    }
  }

  return rows;
}


function connectExports() {
  elements.exportScenarioCsv.addEventListener("click", () => {
    const content = rowsToCsv(state.activeResult.populationRows);
    downloadFile("population_by_year_age.csv", content, "text/csv;charset=utf-8");
  });

  elements.exportPyramidsCsv.addEventListener("click", () => {
    const content = rowsToCsv(buildAllYearsPyramidRows(state.activeResult));
    downloadFile("all_years_age_distribution.csv", content, "text/csv;charset=utf-8");
  });

  elements.exportSummaryCsv.addEventListener("click", () => {
    const content = rowsToCsv(state.activeResult.summaryRows);
    downloadFile("summary.csv", content, "text/csv;charset=utf-8");
  });

  elements.exportPyramidImage.addEventListener("click", async () => {
    const viewName = currentPopulationView() === "pyramid" ? "pyramid" : "age_distribution";
    await Plotly.downloadImage(elements.pyramidChart, {
      format: "png",
      filename: `world_analytic_${viewName}`,
      width: 1200,
      height: 900,
    });
  });

  elements.resetScenario.addEventListener("click", async () => {
    elements.uptakeMode.value = "threshold";
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
    elements.thresholdAge.value = `${state.manifest.default_threshold_age}`;
    elements.thresholdProbability.value = `${state.manifest.default_threshold_probability ?? 100}`;
    elements.rolloutCurve.value = normalizeRolloutCurve(state.manifest.default_rollout_curve);
    elements.rolloutLaunchProbability.value = `${state.manifest.default_rollout_launch_probability ?? 10}`;
    elements.rolloutMaxProbability.value = `${state.manifest.default_rollout_max_probability ?? 50}`;
    elements.rolloutRampYears.value = `${state.manifest.default_rollout_ramp_years ?? 12}`;
    elements.rolloutTakeoffYears.value = `${state.manifest.default_rollout_takeoff_years ?? 8}`;
    renderActivePresetOptions("banded", defaultPresetIdForMode("banded"));
    applyPresetToActiveControls(defaultPresetIdForMode("banded"));
    syncMainViewToggle("results");
    syncUptakeModeToggle();
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
  elements.areaSelect.addEventListener("change", async () => {
    await selectArea(elements.areaSelect.value);
  });

  for (const button of mainViewButtons) {
    button.addEventListener("click", () => {
      const nextView = button.dataset.mainView;
      if (!nextView || nextView === currentMainView()) {
        return;
      }
      syncMainViewToggle(nextView);
      updateUrl(buildActiveScenario(), buildCompareScenario(), currentYear());
    });
  }

  if (elements.mainViewToggle) {
    elements.mainViewToggle.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) {
        return;
      }

      event.preventDefault();
      const views = ["results", "methods"];
      const currentIndex = views.indexOf(currentMainView());
      const direction = event.key === "ArrowRight" ? 1 : -1;
      const nextIndex = (currentIndex + direction + views.length) % views.length;
      syncMainViewToggle(views[nextIndex]);
      mainViewButtons[nextIndex]?.focus();
      updateUrl(buildActiveScenario(), buildCompareScenario(), currentYear());
    });
  }

  for (const button of areaViewButtons) {
    button.addEventListener("click", () => {
      const nextView = button.dataset.areaView;
      if (!nextView || nextView === currentAreaView()) {
        return;
      }
      syncAreaViewToggle(nextView);
    });
  }

  for (const button of strategyButtons) {
    button.addEventListener("click", async () => {
      const nextMode = button.dataset.uptakeMode;
      if (!nextMode || nextMode === elements.uptakeMode.value) {
        return;
      }

      elements.uptakeMode.value = nextMode;
      if (nextMode === "banded") {
        renderActivePresetOptions("banded", elements.presetSelect.value || defaultPresetIdForMode("banded"));
        applyPresetToActiveControls(elements.presetSelect.value || defaultPresetIdForMode("banded"));
      }
      syncUptakeModeToggle();
      await rerender();
    });
  }

  for (const button of populationViewButtons) {
    button.addEventListener("click", () => {
      const nextView = button.dataset.populationView;
      if (!nextView || nextView === currentPopulationView()) {
        return;
      }

      syncPopulationViewToggle(nextView);
      const selectedYear = currentYear();
      renderPopulationChart(
        elements.pyramidChart,
        state.activeResult,
        selectedYear,
        `Active scenario · ${selectedYear}`,
        { untreated: "#aeb8cf", treated: "#16314d" },
      );
      renderPopulationChart(
        elements.comparePyramidChart,
        state.compareResult,
        selectedYear,
        `Comparison scenario · ${selectedYear}`,
        { untreated: "#f0b29f", treated: "#8e2f21" },
      );
      renderMethodsStage(buildActiveScenario());
      updateUrl(buildActiveScenario(), buildCompareScenario(), selectedYear);
    });
  }

  elements.presetSelect.addEventListener("change", async () => {
    if (elements.uptakeMode.value !== "banded") {
      return;
    }
    applyPresetToActiveControls(elements.presetSelect.value);
    await rerender();
  });

  elements.comparePresetSelect.addEventListener("change", rerender);

  elements.targetSelect.addEventListener("change", async () => {
    updateFactorOptions(elements.targetSelect, elements.factorSelect);
    syncFactorInput(elements.targetSelect, elements.factorInput);
    await rerender();
  });

  elements.branchSelect.addEventListener("change", async () => {
    updateFactorOptions(elements.targetSelect, elements.factorSelect, elements.factorSelect.value);
    syncFactorInput(elements.targetSelect, elements.factorInput, elements.factorSelect.value);
    await rerender();
  });

  elements.compareTargetSelect.addEventListener("change", async () => {
    updateFactorOptions(elements.compareTargetSelect, elements.compareFactorSelect);
    syncFactorInput(elements.compareTargetSelect, elements.compareFactorInput);
    await rerender();
  });

  elements.compareBranchSelect.addEventListener("change", async () => {
    updateFactorOptions(elements.compareTargetSelect, elements.compareFactorSelect, elements.compareFactorSelect.value);
    syncFactorInput(elements.compareTargetSelect, elements.compareFactorInput, elements.compareFactorSelect.value);
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
    elements.thresholdProbability,
    elements.rolloutCurve,
    elements.rolloutLaunchProbability,
    elements.rolloutMaxProbability,
    elements.rolloutRampYears,
    elements.rolloutTakeoffYears,
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
    renderPopulationChart(
      elements.pyramidChart,
      state.activeResult,
      selectedYear,
      `Active scenario · ${selectedYear}`,
      { untreated: "#aeb8cf", treated: "#16314d" },
    );
    renderPopulationChart(
      elements.comparePyramidChart,
      state.compareResult,
      selectedYear,
      `Comparison scenario · ${selectedYear}`,
      { untreated: "#f0b29f", treated: "#8e2f21" },
    );
    renderMethodsStage(buildActiveScenario());
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
  state.fetchJson = fetchJson;

  state.manifest = await fetchJson(manifestUrl);

  const resolvePath = (relativePath) => new URL(relativePath, manifestUrl).href;
  state.manifest.paths.sr_interventions_root = resolvePath(state.manifest.paths.sr_interventions_root);
  state.manifest.paths.scenario_catalog = resolvePath(state.manifest.paths.scenario_catalog);
  state.manifest.areas = (state.manifest.areas || []).map((area) => {
    return {
      ...area,
      paths: {
        demography: resolvePath(area.paths.demography),
        analytic_presets: resolvePath(area.paths.analytic_presets),
        calibration: resolvePath(area.paths.calibration),
      },
    };
  });

  const scenarioCatalog = await fetchJson(state.manifest.paths.scenario_catalog);
  state.scenarioCatalog = scenarioCatalog.presets;

  const params = new URLSearchParams(window.location.search);
  const requestedArea = params.get("area") || state.manifest.default_area;
  await loadAreaAssets(requestedArea);
}


function populateControls({ preserveSelections = false } = {}) {
  const previous = preserveSelections ? captureControlState() : null;

  fillAreaSelect(elements.areaSelect);
  fillSelect(elements.launchYear, state.demography.years);
  fillSelect(elements.projectionEndYear, state.demography.years.slice(1));
  fillSelect(elements.branchSelect, state.manifest.branch_options, branchLabel);
  fillSelect(elements.compareBranchSelect, state.manifest.branch_options, branchLabel);
  fillTargetSelect(elements.targetSelect);
  fillTargetSelect(elements.compareTargetSelect);
  fillSelect(elements.heteroMode, ["off", "on"], (value) => value === "off" ? "usa_2019" : "usa_2019 + Xc heterogeneity");
  fillSelect(elements.compareHeteroMode, ["off", "on"], (value) => value === "off" ? "usa_2019" : "usa_2019 + Xc heterogeneity");
  fillPresetSelect(elements.comparePresetSelect);
  fillAnalyticPresetSelect(elements.analyticPresetSelect);
  fillAnalyticPresetSelect(elements.compareAnalyticPresetSelect);
  renderActivePresetOptions("banded", previous?.preset || defaultPresetIdForMode("banded"));
  configureFactorInput(elements.factorInput);
  configureFactorInput(elements.compareFactorInput);

  elements.areaSelect.value = state.activeArea.slug;
  elements.branchSelect.value = state.manifest.default_branch;
  elements.compareBranchSelect.value = state.manifest.default_branch;
  elements.targetSelect.value = previous?.target || state.manifest.default_target;
  elements.compareTargetSelect.value = previous?.compareTarget || state.manifest.default_target;
  updateFactorOptions(elements.targetSelect, elements.factorSelect);
  updateFactorOptions(elements.compareTargetSelect, elements.compareFactorSelect, "1.00");
  syncFactorInput(elements.targetSelect, elements.factorInput, previous?.factor);
  syncFactorInput(elements.compareTargetSelect, elements.compareFactorInput, previous?.compareFactor || "1.00");
  elements.heteroMode.value = "off";
  elements.compareHeteroMode.value = "off";
  elements.analyticPresetSelect.value = state.manifest.default_analytic_preset_id;
  elements.compareAnalyticPresetSelect.value = state.manifest.default_analytic_preset_id;
  elements.thresholdAge.max = `${state.demography.ages[state.demography.ages.length - 1]}`;
  elements.comparePresetSelect.value = previous?.comparePreset || state.manifest.default_compare_preset_id;
  elements.launchYear.value = previous?.launchYear && state.demography.years.includes(Number(previous.launchYear))
    ? previous.launchYear
    : `${state.manifest.default_launch_year}`;
  elements.projectionEndYear.value = previous?.projectionEndYear && state.demography.years.slice(1).includes(Number(previous.projectionEndYear))
    ? previous.projectionEndYear
    : `${state.manifest.default_projection_end_year}`;
  elements.thresholdAge.value = previous?.thresholdAge || `${state.manifest.default_threshold_age}`;
  elements.thresholdProbability.value = previous?.thresholdProbability || `${state.manifest.default_threshold_probability ?? 100}`;
  elements.rolloutCurve.value = normalizeRolloutCurve(previous?.rolloutCurve || state.manifest.default_rollout_curve);
  elements.rolloutLaunchProbability.value = previous?.rolloutLaunchProbability || `${state.manifest.default_rollout_launch_probability ?? 10}`;
  elements.rolloutMaxProbability.value = previous?.rolloutMaxProbability || `${state.manifest.default_rollout_max_probability ?? 50}`;
  elements.rolloutRampYears.value = previous?.rolloutRampYears || `${state.manifest.default_rollout_ramp_years ?? 12}`;
  elements.rolloutTakeoffYears.value = previous?.rolloutTakeoffYears || `${state.manifest.default_rollout_takeoff_years ?? 8}`;
  elements.startRule.value = normalizeBandedStartRule(previous?.startRule || state.manifest.default_start_rule);
  elements.band2039.value = previous?.band2039 || `${Math.round(state.manifest.default_bands[0].target_share * 100)}`;
  elements.band4064.value = previous?.band4064 || `${Math.round(state.manifest.default_bands[1].target_share * 100)}`;
  elements.band65Plus.value = previous?.band65Plus || `${Math.round(state.manifest.default_bands[2].target_share * 100)}`;
  elements.uptakeMode.value = previous?.uptakeMode || "threshold";
  renderActivePresetOptions("banded", previous?.preset || defaultPresetIdForMode("banded"));
  syncUptakeModeToggle();
  applyPresetToActiveControls(elements.presetSelect.value || defaultPresetIdForMode("banded"));

  if (previous?.analyticPreset && [...elements.analyticPresetSelect.options].some((option) => option.value === previous.analyticPreset)) {
    elements.analyticPresetSelect.value = previous.analyticPreset;
  }
  if (previous?.compareAnalyticPreset && [...elements.compareAnalyticPresetSelect.options].some((option) => option.value === previous.compareAnalyticPreset)) {
    elements.compareAnalyticPresetSelect.value = previous.compareAnalyticPreset;
  }

  syncMainViewToggle(previous?.mainView || "results");
  syncAreaViewToggle(previous?.areaView || defaultAreaView());
  syncPopulationViewToggle(previous?.populationView || "distribution");
  renderAreaSelector();

  if (!preserveSelections) {
    setControlsFromUrl();
  }
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
