function safeTarget(target) {
  if (target === null || target === undefined || target === "none") {
    return "eta";
  }
  return target;
}


function safeFactor(target, factor) {
  if (target === null || target === undefined || target === "none") {
    return 1.0;
  }
  return Number(factor);
}


function targetSlug(target) {
  return target === "Xc" ? "xc" : "eta";
}


function factorKey(factor) {
  return Number(factor).toFixed(2);
}


export function buildSrAssetUrl(srRootUrl, target, heteroMode, factor) {
  const safeRoot = srRootUrl.endsWith("/") ? srRootUrl : `${srRootUrl}/`;
  const url = new URL(`${targetSlug(target)}/${heteroMode}/${factorKey(factor)}.json`, safeRoot);
  return url.href;
}


export function buildAllSexWppHazard(demography, year) {
  const yearKey = `${year}`;
  const mortality = demography.mortality[yearKey];
  const population = demography.population[yearKey];

  if (!mortality || !population) {
    throw new Error(`Missing demography inputs for year ${year}`);
  }

  const ages = demography.ages;
  const hazard = new Array(ages.length).fill(0);

  for (let age = 0; age < ages.length; age += 1) {
    const malePopulation = population.male[age];
    const femalePopulation = population.female[age];
    const totalPopulation = malePopulation + femalePopulation;

    if (totalPopulation <= 0) {
      continue;
    }

    const weightedHazard = (mortality.male[age] * malePopulation) + (mortality.female[age] * femalePopulation);
    hazard[age] = weightedHazard / totalPopulation;
  }

  for (let age = ages.length - 1; age >= 0; age -= 1) {
    if (hazard[age] <= 0) {
      continue;
    }

    for (let fillAge = age + 1; fillAge < ages.length; fillAge += 1) {
      hazard[fillAge] = hazard[age];
    }
    break;
  }

  return hazard;
}


export function survivalFromHazardCurve(hazard) {
  const survival = new Array(hazard.length + 1).fill(1);

  for (let age = 0; age < hazard.length; age += 1) {
    survival[age + 1] = survival[age] * Math.exp(-Number(hazard[age]));
  }

  return survival;
}


function analyticExponent(target, factor, attainedAge, startAge, params) {
  const eta = Number(params.eta);
  const beta = Number(params.beta);
  const epsilon = Number(params.epsilon);
  const xc = Number(params.Xc);

  if (target === "Xc") {
    return -(((factor - 1) * xc) / epsilon) * (beta - (eta * attainedAge));
  }

  if (target === "eta") {
    return -((xc / epsilon) * (eta - (factor * eta)) * (attainedAge - startAge));
  }

  throw new Error(`Unsupported target: ${target}`);
}


export function buildAnalyticMultiplierRow({ target, factor, startAge, ages, analyticPreset }) {
  const row = new Array(ages.length).fill(1);
  if (Math.abs(Number(factor) - 1) < 1e-12) {
    return row;
  }

  for (let ageIndex = 0; ageIndex < ages.length; ageIndex += 1) {
    const attainedAge = Number(ages[ageIndex]);
    if (attainedAge < startAge) {
      continue;
    }

    const exponent = analyticExponent(
      target,
      Number(factor),
      attainedAge,
      Number(startAge),
      analyticPreset.params,
    );
    row[ageIndex] = Math.exp(Math.max(-60, Math.min(60, exponent)));
  }

  return row;
}


export function buildAnalyticInterventionAsset({
  demography,
  target,
  factor,
  launchYear,
  analyticPreset,
}) {
  const ages = demography.ages.slice();
  const startAges = demography.ages.slice();
  const baselineHazard = buildAllSexWppHazard(demography, launchYear);
  const baselineSurvival = survivalFromHazardCurve(baselineHazard);
  const annualHazardMultiplier = [];
  const survivalByStartAge = [];

  for (const startAge of startAges) {
    const multiplierRow = buildAnalyticMultiplierRow({
      target,
      factor,
      startAge,
      ages,
      analyticPreset,
    });
    const treatedHazard = baselineHazard.map((value, ageIndex) => value * multiplierRow[ageIndex]);
    annualHazardMultiplier.push(multiplierRow);
    survivalByStartAge.push(survivalFromHazardCurve(treatedHazard));
  }

  return {
    target,
    factor: Number(factor),
    hetero_mode: "off",
    start_ages: startAges,
    ages,
    annual_hazard_multiplier: annualHazardMultiplier,
    baseline_survival: baselineSurvival,
    survival_by_start_age: survivalByStartAge,
  };
}


function cacheValue(cache, key, valueFactory) {
  if (cache.has(key)) {
    return cache.get(key);
  }

  const pending = Promise.resolve()
    .then(valueFactory)
    .then((value) => {
      cache.set(key, value);
      return value;
    })
    .catch((error) => {
      cache.delete(key);
      throw error;
    });

  cache.set(key, pending);
  return pending;
}


export function createInterventionStore({
  manifest,
  demography,
  analyticPresets,
  fetchJson,
}) {
  const cache = new Map();
  const presetById = new Map();

  for (const preset of analyticPresets.presets) {
    presetById.set(preset.id, preset);
  }

  async function getSrAsset({ target, heteroMode, factor }) {
    const cacheKey = `sr|${safeTarget(target)}|${heteroMode}|${factorKey(factor)}`;
    return cacheValue(cache, cacheKey, async () => {
      const url = buildSrAssetUrl(
        manifest.paths.sr_interventions_root,
        safeTarget(target),
        heteroMode,
        factor,
      );
      return fetchJson(url);
    });
  }

  async function getAnalyticAsset({ target, factor, launchYear, analyticPresetId }) {
    const safePresetId = analyticPresetId || manifest.default_analytic_preset_id;
    const preset = presetById.get(safePresetId);
    if (!preset) {
      throw new Error(`Unknown analytic preset: ${safePresetId}`);
    }

    const cacheKey = [
      "analytic",
      safeTarget(target),
      factorKey(factor),
      `${launchYear}`,
      safePresetId,
    ].join("|");

    return cacheValue(cache, cacheKey, () => {
      return buildAnalyticInterventionAsset({
        demography,
        target: safeTarget(target),
        factor,
        launchYear,
        analyticPreset: preset,
      });
    });
  }

  async function getAsset(scenario) {
    const target = safeTarget(scenario.target);
    const factor = safeFactor(scenario.target, scenario.factor);

    if (scenario.branch === "analytic_arm") {
      return getAnalyticAsset({
        target,
        factor,
        launchYear: Number(scenario.launch_year),
        analyticPresetId: scenario.analytic_preset_id,
      });
    }

    return getSrAsset({
      target,
      heteroMode: scenario.hetero_mode,
      factor,
    });
  }

  return {
    getAsset,
  };
}
