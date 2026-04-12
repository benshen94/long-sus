function zeroArray(length) {
  return new Array(length).fill(0);
}


function zeroMatrix(rows, cols) {
  return Array.from({ length: rows }, () => zeroArray(cols));
}


function cloneArray(values) {
  return values.slice();
}


function clonePopulation(population) {
  return {
    male: cloneArray(population.male),
    female: cloneArray(population.female),
  };
}


function cloneTreated(treated) {
  return {
    male: treated.male.map((row) => row.slice()),
    female: treated.female.map((row) => row.slice()),
  };
}


function tailPopulationWeights(mx, tailLength) {
  if (tailLength <= 0) {
    return [1];
  }

  const survival = Math.exp(-Math.max(0, Number(mx)));
  const weights = new Array(tailLength + 1).fill(1);

  for (let index = 1; index < weights.length; index += 1) {
    weights[index] = weights[index - 1] * survival;
  }

  const total = weights.reduce((sum, value) => sum + value, 0);
  if (total <= 0) {
    return weights.map(() => 1 / weights.length);
  }

  return weights.map((value) => value / total);
}


function tailLogHazardSlope(mxByAge, openAge, lookbackYears = 5) {
  if (openAge <= 0) {
    return null;
  }

  const startAge = Math.max(0, openAge - lookbackYears);
  const window = mxByAge.slice(startAge, openAge + 1);
  const positiveWindow = window.filter((value) => value > 0);
  if (positiveWindow.length < 2) {
    return null;
  }

  return (
    Math.log(positiveWindow[positiveWindow.length - 1]) - Math.log(positiveWindow[0])
  ) / (positiveWindow.length - 1);
}


function extendMortalityTail(mortalityByAge) {
  const mx = cloneArray(mortalityByAge);
  let lastPositiveAge = -1;

  for (let age = mx.length - 1; age >= 0; age -= 1) {
    if (mx[age] > 0) {
      lastPositiveAge = age;
      break;
    }
  }

  if (lastPositiveAge < 0 || lastPositiveAge >= mx.length - 1) {
    return mx;
  }

  if (lastPositiveAge !== 100) {
    for (let age = lastPositiveAge + 1; age < mx.length; age += 1) {
      mx[age] = mx[lastPositiveAge];
    }
    return mx;
  }

  const logSlope = tailLogHazardSlope(mx, lastPositiveAge);
  if (logSlope === null) {
    for (let age = lastPositiveAge + 1; age < mx.length; age += 1) {
      mx[age] = mx[lastPositiveAge];
    }
    return mx;
  }

  for (let age = lastPositiveAge + 1; age < mx.length; age += 1) {
    const yearsPastOpenAge = age - lastPositiveAge;
    mx[age] = mx[lastPositiveAge] * Math.exp(logSlope * yearsPastOpenAge);
  }

  return mx;
}


function tailPopulationWeightsFromCurve(mxByAge) {
  if (mxByAge.length === 0) {
    return [1];
  }

  const weights = new Array(mxByAge.length).fill(1);
  for (let index = 1; index < weights.length; index += 1) {
    const annualSurvival = Math.exp(-Math.max(0, Number(mxByAge[index - 1])));
    weights[index] = weights[index - 1] * annualSurvival;
  }

  const total = weights.reduce((sum, value) => sum + value, 0);
  if (total <= 0) {
    return weights.map(() => 1 / weights.length);
  }

  return weights.map((value) => value / total);
}


function extendPopulationTail(populationByAge, mortalityByAge) {
  const population = cloneArray(populationByAge);
  let lastPositiveAge = -1;

  for (let age = population.length - 1; age >= 0; age -= 1) {
    if (population[age] > 0) {
      lastPositiveAge = age;
      break;
    }
  }

  if (lastPositiveAge < 0 || lastPositiveAge >= population.length - 1) {
    return population;
  }

  if (lastPositiveAge > 100) {
    return population;
  }

  const openAgePopulation = Number(population[lastPositiveAge]);
  if (openAgePopulation <= 0) {
    return population;
  }

  const extendedMortality = extendMortalityTail(mortalityByAge);
  const tailWeights = tailPopulationWeightsFromCurve(extendedMortality.slice(lastPositiveAge));
  for (let offset = 0; offset < tailWeights.length; offset += 1) {
    population[lastPositiveAge + offset] = openAgePopulation * tailWeights[offset];
  }

  return population;
}


function projectOneYearNoMigration(population, mortality, fertility, sexRatioAtBirth) {
  const nextPopulation = {
    male: zeroArray(population.male.length),
    female: zeroArray(population.female.length),
  };

  const births = computeBirths(population.female, fertility, sexRatioAtBirth);
  nextPopulation.male[0] = births.maleBirths;
  nextPopulation.female[0] = births.femaleBirths;

  for (const sex of ["male", "female"]) {
    const survival = annualSurvivalFromMx(mortality[sex]);
    const survivors = population[sex].map((value, age) => value * survival[age]);
    const aged = ageSurvivors(survivors);

    for (let age = 0; age < aged.length; age += 1) {
      nextPopulation[sex][age] += aged[age];
    }
  }

  return nextPopulation;
}


function deriveMigrationResiduals(demography) {
  const residuals = {};
  const years = demography.years.slice().sort((a, b) => a - b);

  for (let index = 0; index < years.length - 1; index += 1) {
    const year = years[index];
    const nextYear = years[index + 1];
    const projected = projectOneYearNoMigration(
      demography.population[String(year)],
      demography.mortality[String(year)],
      demography.fertility[String(year)],
      demography.sex_ratio_at_birth[String(year)],
    );
    const target = demography.population[String(nextYear)];

    residuals[String(year)] = {
      male: target.male.map((value, age) => value - projected.male[age]),
      female: target.female.map((value, age) => value - projected.female[age]),
    };
  }

  return residuals;
}


export function normalizeDemography(demography) {
  const normalized = {
    ...demography,
    population: {},
    mortality: {},
    migration_residual: {},
  };

  for (const year of demography.years) {
    const yearKey = String(year);
    normalized.mortality[yearKey] = {
      male: extendMortalityTail(demography.mortality[yearKey].male),
      female: extendMortalityTail(demography.mortality[yearKey].female),
    };
    normalized.population[yearKey] = {
      male: extendPopulationTail(
        demography.population[yearKey].male,
        normalized.mortality[yearKey].male,
      ),
      female: extendPopulationTail(
        demography.population[yearKey].female,
        normalized.mortality[yearKey].female,
      ),
    };
  }

  normalized.migration_residual = deriveMigrationResiduals(normalized);
  return normalized;
}


function resolveAgeBands(bands, maxAge) {
  const resolved = [];
  let treatedBefore = 0;

  for (const band of bands) {
    const endAge = band.end_age === null ? maxAge : band.end_age;
    const targetShare = Math.max(0, Math.min(1, band.target_share));

    let conditionalShare = 0;
    if (treatedBefore < 1 && targetShare > treatedBefore) {
      conditionalShare = (targetShare - treatedBefore) / (1 - treatedBefore);
      conditionalShare = Math.max(0, Math.min(1, conditionalShare));
    }

    resolved.push({
      startAge: band.start_age,
      endAge,
      conditionalShare,
    });
    treatedBefore = targetShare;
  }

  return resolved;
}


function clampedProbability(value) {
  return Math.max(0, Math.min(1, Number(value)));
}


export function rolloutProbabilityForYear(scenario, year) {
  if (year < scenario.launch_year) {
    return 0;
  }

  const launchProbability = clampedProbability(scenario.rollout_launch_probability ?? 0);
  const maxProbability = clampedProbability(
    Math.max(Number(scenario.rollout_max_probability ?? launchProbability), launchProbability),
  );
  if (maxProbability <= launchProbability) {
    return launchProbability;
  }

  const yearsSinceLaunch = year - scenario.launch_year;

  if (scenario.rollout_curve === "linear") {
    const rampYears = Math.max(1, Number(scenario.rollout_ramp_years ?? 1));
    const progress = Math.min(yearsSinceLaunch / rampYears, 1);
    return launchProbability + ((maxProbability - launchProbability) * progress);
  }

  if (scenario.rollout_curve === "logistic") {
    const takeoffYears = Math.max(1, Number(scenario.rollout_takeoff_years ?? 1));
    const baseline = 1 / (1 + Math.exp(0.5 * takeoffYears));
    const current = 1 / (1 + Math.exp(-0.5 * (yearsSinceLaunch - takeoffYears)));
    const scaled = Math.max(0, Math.min(1, (current - baseline) / (1 - baseline)));
    return launchProbability + ((maxProbability - launchProbability) * scaled);
  }

  throw new Error(`Unsupported rollout curve: ${scenario.rollout_curve}`);
}


function thresholdProbability(age, year, scenario) {
  const probability = clampedProbability(scenario.threshold_probability ?? 1);
  if (scenario.threshold_age === null || scenario.threshold_age === undefined) {
    return 0;
  }
  if (year < scenario.launch_year) {
    return 0;
  }
  if (age < scenario.threshold_age) {
    return 0;
  }
  if (year === scenario.launch_year) {
    return probability;
  }
  if (age === scenario.threshold_age) {
    return probability;
  }
  return 0;
}


function rolloutProbability(age, year, scenario) {
  if (scenario.threshold_age === null || scenario.threshold_age === undefined) {
    return 0;
  }
  if (year < scenario.launch_year) {
    return 0;
  }
  if (age < scenario.threshold_age) {
    return 0;
  }
  return rolloutProbabilityForYear(scenario, year);
}


function absoluteProbability(age, year, scenario, band) {
  if (year < scenario.launch_year) {
    return 0;
  }
  if (age < band.startAge || age > band.endAge) {
    return 0;
  }
  if (year === scenario.launch_year) {
    return band.conditionalShare;
  }
  if (age === band.startAge) {
    return band.conditionalShare;
  }
  return 0;
}


function equalProbability(age, year, scenario, band) {
  if (year < scenario.launch_year) {
    return 0;
  }
  if (age < band.startAge || age > band.endAge) {
    return 0;
  }

  const bandLength = band.endAge - band.startAge + 1;
  if (bandLength <= 0 || band.conditionalShare <= 0) {
    return 0;
  }

  return 1 - Math.pow(1 - band.conditionalShare, 1 / bandLength);
}


function uniformProbability(age, year, scenario, band) {
  if (year < scenario.launch_year) {
    return 0;
  }
  if (age < band.startAge || age > band.endAge) {
    return 0;
  }

  const bandLength = band.endAge - band.startAge + 1;
  if (bandLength <= 0 || band.conditionalShare <= 0) {
    return 0;
  }

  const ageIndex = age - band.startAge;
  const denominator = bandLength - (band.conditionalShare * ageIndex);
  if (denominator <= 0) {
    return 0;
  }

  return band.conditionalShare / denominator;
}


export function startProbabilityByAge(scenario, age, year, maxAge) {
  if (scenario.target === null || scenario.target === "none") {
    return 0;
  }

  if (scenario.uptake_mode === "threshold") {
    return thresholdProbability(age, year, scenario);
  }

  if (scenario.uptake_mode === "rollout") {
    return rolloutProbability(age, year, scenario);
  }

  if (scenario.uptake_mode !== "banded") {
    throw new Error(`Unsupported uptake mode: ${scenario.uptake_mode}`);
  }

  const resolvedBands = resolveAgeBands(scenario.bands || [], maxAge);
  for (const band of resolvedBands) {
    if (age < band.startAge || age > band.endAge) {
      continue;
    }

    if (scenario.start_rule_within_band === "absolute") {
      return absoluteProbability(age, year, scenario, band);
    }
    if (scenario.start_rule_within_band === "equal_probabilities") {
      return equalProbability(age, year, scenario, band);
    }
    if (scenario.start_rule_within_band === "uniform_start_age") {
      return uniformProbability(age, year, scenario, band);
    }
    throw new Error(`Unsupported start rule: ${scenario.start_rule_within_band}`);
  }

  return 0;
}


export function buildStartProbabilityTable(scenario, years, ages) {
  const table = [];
  const maxAge = ages[ages.length - 1];

  for (const year of years) {
    const row = [];
    for (const age of ages) {
      const value = startProbabilityByAge(scenario, age, year, maxAge);
      row.push(Math.max(0, Math.min(1, value)));
    }
    table.push(row);
  }

  return table;
}


export function buildLifetimeStartWeights(scenario, startAges) {
  const weights = zeroArray(startAges.length);
  let untreatedShare = 1;

  if (scenario.target === null || scenario.target === "none") {
    return { weights, untreatedShare: 1 };
  }

  if (scenario.uptake_mode === "threshold") {
    if (scenario.threshold_age === null || scenario.threshold_age === undefined) {
      return { weights, untreatedShare: 1 };
    }
    const index = startAges.indexOf(Number(scenario.threshold_age));
    if (index === -1) {
      return { weights, untreatedShare: 1 };
    }
    const probability = Math.max(0, Math.min(1, Number(scenario.threshold_probability ?? 1)));
    weights[index] = probability;
    return { weights, untreatedShare: 1 - probability };
  }

  if (scenario.uptake_mode === "rollout") {
    if (scenario.threshold_age === null || scenario.threshold_age === undefined) {
      return { weights, untreatedShare: 1 };
    }

    for (let age = Number(scenario.threshold_age); age <= startAges[startAges.length - 1]; age += 1) {
      const index = startAges.indexOf(age);
      if (index === -1) {
        continue;
      }

      if (untreatedShare <= 0) {
        return { weights, untreatedShare: 0 };
      }

      const probability = rolloutProbabilityForYear(scenario, scenario.launch_year + age);
      const startShare = untreatedShare * probability;
      weights[index] += startShare;
      untreatedShare -= startShare;
    }

    untreatedShare = Math.max(0, Math.min(1, untreatedShare));
    return { weights, untreatedShare };
  }

  const resolvedBands = resolveAgeBands(scenario.bands || [], startAges[startAges.length - 1]);
  for (const band of resolvedBands) {
    if (untreatedShare <= 0) {
      return { weights, untreatedShare: 0 };
    }

    if (scenario.start_rule_within_band === "absolute") {
      const index = startAges.indexOf(band.startAge);
      if (index !== -1) {
        const startShare = untreatedShare * band.conditionalShare;
        weights[index] += startShare;
        untreatedShare -= startShare;
      }
      continue;
    }

    for (let age = band.startAge; age <= band.endAge; age += 1) {
      const index = startAges.indexOf(age);
      if (index === -1) {
        continue;
      }

      let probability = 0;
      if (scenario.start_rule_within_band === "equal_probabilities") {
        probability = equalProbability(age, scenario.launch_year + 1, scenario, band);
      } else {
        probability = uniformProbability(age, scenario.launch_year + 1, scenario, band);
      }

      const startShare = untreatedShare * probability;
      weights[index] += startShare;
      untreatedShare -= startShare;
    }
  }

  untreatedShare = Math.max(0, Math.min(1, untreatedShare));
  return { weights, untreatedShare };
}


export function buildCohortSurvivalCurve(interventionAsset, scenario) {
  const { weights, untreatedShare } = buildLifetimeStartWeights(scenario, interventionAsset.start_ages);
  const curve = interventionAsset.baseline_survival.map((value) => value * untreatedShare);

  for (let row = 0; row < interventionAsset.start_ages.length; row += 1) {
    const weight = weights[row];
    if (weight <= 0) {
      continue;
    }
    const survivalRow = interventionAsset.survival_by_start_age[row];
    for (let age = 0; age < curve.length; age += 1) {
      curve[age] += survivalRow[age] * weight;
    }
  }

  return curve;
}


export function annualSurvivalFromMx(mxByAge) {
  if (Array.isArray(mxByAge[0])) {
    return mxByAge.map((row) => row.map((value) => Math.exp(-value)));
  }
  return mxByAge.map((value) => Math.exp(-value));
}


export function computeBirths(femalePopulation, fertilityByAge, sexRatioAtBirth) {
  let totalBirths = 0;
  for (let index = 0; index < femalePopulation.length; index += 1) {
    totalBirths += femalePopulation[index] * fertilityByAge[index];
  }

  const maleShare = sexRatioAtBirth / (1 + sexRatioAtBirth);
  const maleBirths = totalBirths * maleShare;
  const femaleBirths = totalBirths - maleBirths;

  return { maleBirths, femaleBirths, totalBirths };
}


function ageSurvivors(survivors) {
  const aged = zeroArray(survivors.length);
  for (let age = 1; age < survivors.length; age += 1) {
    aged[age] = survivors[age - 1];
  }
  aged[survivors.length - 1] += survivors[survivors.length - 1];
  return aged;
}


function ageTreatedSurvivors(survivors) {
  const aged = zeroMatrix(survivors.length, survivors[0].length);
  for (let row = 0; row < survivors.length; row += 1) {
    for (let age = 1; age < survivors[row].length; age += 1) {
      aged[row][age] = survivors[row][age - 1];
    }
    aged[row][survivors[row].length - 1] += survivors[row][survivors[row].length - 1];
  }
  return aged;
}


function sumTreatedByAge(treatedMatrix) {
  const totals = zeroArray(treatedMatrix[0].length);
  for (let row = 0; row < treatedMatrix.length; row += 1) {
    for (let age = 0; age < treatedMatrix[row].length; age += 1) {
      totals[age] += treatedMatrix[row][age];
    }
  }
  return totals;
}


function pickYears(inputs, projectionEndYear) {
  if (projectionEndYear === null || projectionEndYear === undefined) {
    return inputs.years.slice();
  }

  const years = inputs.years.filter((year) => year <= projectionEndYear);
  if (years.length < 2) {
    throw new Error("Projection requires at least two years");
  }
  return years;
}


function positiveResidualTreatedShare(age, year, scenario, maxAge, currentShare) {
  if (!scenario || scenario.target === null || scenario.target === "none") {
    return currentShare;
  }

  if (year < scenario.launch_year) {
    return currentShare;
  }

  if (scenario.uptake_mode === "threshold") {
    if (scenario.threshold_age === null || scenario.threshold_age === undefined) {
      return currentShare;
    }
    if (age < scenario.threshold_age) {
      return 0;
    }
    return clampedProbability(scenario.threshold_probability ?? 1);
  }

  if (scenario.uptake_mode === "rollout") {
    if (scenario.threshold_age === null || scenario.threshold_age === undefined) {
      return currentShare;
    }
    if (age < scenario.threshold_age) {
      return 0;
    }
    return rolloutProbabilityForYear(scenario, year);
  }

  if (scenario.uptake_mode !== "banded") {
    return currentShare;
  }

  const resolvedBands = resolveAgeBands(scenario.bands || [], maxAge);
  for (const band of resolvedBands) {
    if (age < band.startAge || age > band.endAge) {
      continue;
    }

    if (scenario.start_rule_within_band === "absolute") {
      return band.conditionalShare;
    }

    return currentShare;
  }

  return currentShare;
}


function addPositiveResidualToTreatedBuckets(treatedMatrix, age, treatedDelta, treatedByAge) {
  if (treatedDelta <= 0) {
    return;
  }

  if (treatedByAge > 0) {
    for (let row = 0; row < treatedMatrix.length; row += 1) {
      const rowShare = treatedMatrix[row][age] / treatedByAge;
      treatedMatrix[row][age] += treatedDelta * rowShare;
    }
    return;
  }

  const rowIndex = Math.min(age, treatedMatrix.length - 1);
  if (rowIndex < 0) {
    return;
  }
  treatedMatrix[rowIndex][age] += treatedDelta;
}


function applyMigrationResidual(state, residual, scenario, year, maxAge) {
  if (!residual) {
    return {
      untreated: clonePopulation(state.untreated),
      treated: cloneTreated(state.treated),
    };
  }

  const untreated = clonePopulation(state.untreated);
  const treated = cloneTreated(state.treated);

  for (const sex of ["male", "female"]) {
    const treatedByAge = sumTreatedByAge(treated[sex]);

    for (let age = 0; age < residual[sex].length; age += 1) {
      const delta = residual[sex][age];
      const total = untreated[sex][age] + treatedByAge[age];

      if (delta >= 0) {
        const currentTreatedShare = total > 0 ? treatedByAge[age] / total : 0;
        const treatedShare = positiveResidualTreatedShare(age, year + 1, scenario, maxAge, currentTreatedShare);
        const safeTreatedShare = Math.max(0, Math.min(1, treatedShare));
        const treatedDelta = delta * safeTreatedShare;
        const untreatedDelta = delta - treatedDelta;

        untreated[sex][age] += untreatedDelta;
        addPositiveResidualToTreatedBuckets(treated[sex], age, treatedDelta, treatedByAge[age]);
        continue;
      }

      if (total <= 0) {
        continue;
      }

      const untreatedShare = untreated[sex][age] / total;
      const treatedShare = treatedByAge[age] / total;

      untreated[sex][age] = Math.max(0, untreated[sex][age] + (delta * untreatedShare));
      if (treatedByAge[age] <= 0) {
        continue;
      }

      const treatedDelta = delta * treatedShare;
      for (let row = 0; row < treated[sex].length; row += 1) {
        const share = treated[sex][row][age] / treatedByAge[age];
        treated[sex][row][age] = Math.max(0, treated[sex][row][age] + (treatedDelta * share));
      }
    }
  }

  return { untreated, treated };
}


function weightedMedianAge(totalPopulation) {
  const total = totalPopulation.reduce((sum, value) => sum + value, 0);
  if (total <= 0) {
    return 0;
  }

  const midpoint = total / 2;
  let cumulative = 0;
  for (let age = 0; age < totalPopulation.length; age += 1) {
    cumulative += totalPopulation[age];
    if (cumulative >= midpoint) {
      return age;
    }
  }

  return totalPopulation.length - 1;
}


function recordPopulationRows(rows, scenario, year, untreated, treated) {
  const rolloutMetadata = {
    rollout_curve: scenario.rollout_curve,
    rollout_launch_probability: Number(scenario.rollout_launch_probability ?? 0),
    rollout_max_probability: Number(scenario.rollout_max_probability ?? 0),
    rollout_ramp_years: Number(scenario.rollout_ramp_years ?? 0),
    rollout_takeoff_years: Number(scenario.rollout_takeoff_years ?? 0),
  };
  for (const sex of ["male", "female"]) {
    const treatedByAge = sumTreatedByAge(treated[sex]);
    for (let age = 0; age < untreated[sex].length; age += 1) {
      const total = untreated[sex][age] + treatedByAge[age];
      rows.push({
        scenario: scenario.name,
        scenario_label: scenario.label || scenario.name,
        scheme_id: scenario.scheme_id || scenario.name,
        country: scenario.country,
        mode: scenario.mode,
        variant: scenario.demo_variant,
        year,
        sex,
        age,
        launch_year: scenario.launch_year,
        uptake_mode: scenario.uptake_mode,
        threshold_age: scenario.threshold_age ?? -1,
        threshold_probability: Number(scenario.threshold_probability ?? 1),
        start_rule_within_band: scenario.start_rule_within_band,
        target: scenario.target || "none",
        factor: scenario.factor,
        branch: scenario.branch,
        analytic_preset_id: scenario.analytic_preset_id || "",
        hetero_mode: scenario.hetero_mode,
        migration_mode: scenario.migration_mode,
        population_count: total,
        treated_population_count: treatedByAge[age],
        untreated_population_count: untreated[sex][age],
        ...rolloutMetadata,
      });
    }
  }
}


function recordSummaryRow(rows, scenario, year, untreated, treated, births, deaths) {
  const rolloutMetadata = {
    rollout_curve: scenario.rollout_curve,
    rollout_launch_probability: Number(scenario.rollout_launch_probability ?? 0),
    rollout_max_probability: Number(scenario.rollout_max_probability ?? 0),
    rollout_ramp_years: Number(scenario.rollout_ramp_years ?? 0),
    rollout_takeoff_years: Number(scenario.rollout_takeoff_years ?? 0),
  };
  const treatedMale = sumTreatedByAge(treated.male);
  const treatedFemale = sumTreatedByAge(treated.female);
  const maleTotal = untreated.male.map((value, age) => value + treatedMale[age]);
  const femaleTotal = untreated.female.map((value, age) => value + treatedFemale[age]);
  const combined = maleTotal.map((value, age) => value + femaleTotal[age]);
  const totalPopulation = combined.reduce((sum, value) => sum + value, 0);
  const treatedPopulation = treatedMale.reduce((sum, value) => sum + value, 0)
    + treatedFemale.reduce((sum, value) => sum + value, 0);

  let older60 = 0;
  let older65 = 0;
  for (let age = 60; age < combined.length; age += 1) {
    older60 += combined[age];
  }
  for (let age = 65; age < combined.length; age += 1) {
    older65 += combined[age];
  }

  rows.push({
    scenario: scenario.name,
    scenario_label: scenario.label || scenario.name,
    scheme_id: scenario.scheme_id || scenario.name,
    country: scenario.country,
    mode: scenario.mode,
    variant: scenario.demo_variant,
    year,
    launch_year: scenario.launch_year,
    uptake_mode: scenario.uptake_mode,
    threshold_age: scenario.threshold_age ?? -1,
    threshold_probability: Number(scenario.threshold_probability ?? 1),
    start_rule_within_band: scenario.start_rule_within_band,
    target: scenario.target || "none",
    factor: scenario.factor,
    branch: scenario.branch,
    analytic_preset_id: scenario.analytic_preset_id || "",
    hetero_mode: scenario.hetero_mode,
    migration_mode: scenario.migration_mode,
    total_population: totalPopulation,
    treated_population: treatedPopulation,
    treated_share: totalPopulation > 0 ? treatedPopulation / totalPopulation : 0,
    births,
    deaths,
    median_age: weightedMedianAge(combined),
    old_age_share_60_plus: totalPopulation > 0 ? older60 / totalPopulation : 0,
    old_age_share_65_plus: totalPopulation > 0 ? older65 / totalPopulation : 0,
    ...rolloutMetadata,
  });
}


function buildSnapshot(untreated, treated) {
  return {
    untreated: clonePopulation(untreated),
    treatedByAge: {
      male: sumTreatedByAge(treated.male),
      female: sumTreatedByAge(treated.female),
    },
  };
}


export function projectScenario(inputs, scenario, interventionAsset) {
  const years = pickYears(inputs, scenario.projection_end_year);
  const ages = inputs.ages.slice();
  const maxAge = ages[ages.length - 1];
  const startProbabilityTable = buildStartProbabilityTable(scenario, years, ages);
  const startAges = interventionAsset.start_ages.slice();
  const startAgeLookup = new Map(startAges.map((value, index) => [Number(value), index]));

  let untreated = clonePopulation(inputs.population[String(years[0])]);
  let treated = {
    male: zeroMatrix(startAges.length, ages.length),
    female: zeroMatrix(startAges.length, ages.length),
  };

  const populationRows = [];
  const summaryRows = [];
  const snapshots = {};

  recordPopulationRows(populationRows, scenario, years[0], untreated, treated);
  recordSummaryRow(summaryRows, scenario, years[0], untreated, treated, 0, 0);
  snapshots[String(years[0])] = buildSnapshot(untreated, treated);

  for (let yearIndex = 0; yearIndex < years.length - 1; yearIndex += 1) {
    const year = years[yearIndex];
    const startProbabilities = startProbabilityTable[yearIndex];
    const nextUntreated = {
      male: zeroArray(ages.length),
      female: zeroArray(ages.length),
    };
    const nextTreated = {
      male: zeroMatrix(startAges.length, ages.length),
      female: zeroMatrix(startAges.length, ages.length),
    };

    const untreatedAfterStart = clonePopulation(untreated);
    const treatedAfterStart = cloneTreated(treated);

    for (const sex of ["male", "female"]) {
      for (let age = 0; age < ages.length; age += 1) {
        const startProbability = startProbabilities[age];
        if (startProbability <= 0) {
          continue;
        }

        const startAgeIndex = startAgeLookup.get(age);
        if (startAgeIndex === undefined) {
          continue;
        }

        const newTreated = untreatedAfterStart[sex][age] * startProbability;
        untreatedAfterStart[sex][age] -= newTreated;
        treatedAfterStart[sex][startAgeIndex][age] += newTreated;
      }
    }

    const treatedFemale = sumTreatedByAge(treated.female);
    const births = computeBirths(
      untreated.female.map((value, age) => value + treatedFemale[age]),
      inputs.fertility[String(year)],
      inputs.sex_ratio_at_birth[String(year)],
    );

    let deaths = 0;
    for (const sex of ["male", "female"]) {
      const untreatedSurvival = annualSurvivalFromMx(inputs.mortality[String(year)][sex]);
      const treatedSurvival = annualSurvivalFromMx(
        interventionAsset.annual_hazard_multiplier.map((row, ageIndex) => {
          return row.map((multiplier, age) => multiplier * inputs.mortality[String(year)][sex][age]);
        }),
      );

      const untreatedSurvivors = zeroArray(ages.length);
      const treatedSurvivors = zeroMatrix(startAges.length, ages.length);

      for (let age = 0; age < ages.length; age += 1) {
        untreatedSurvivors[age] = untreatedAfterStart[sex][age] * untreatedSurvival[age];
      }

      for (let row = 0; row < startAges.length; row += 1) {
        for (let age = 0; age < ages.length; age += 1) {
          treatedSurvivors[row][age] = treatedAfterStart[sex][row][age] * treatedSurvival[row][age];
        }
      }

      const untreatedDeaths = untreatedAfterStart[sex].reduce((sum, value, age) => sum + value - untreatedSurvivors[age], 0);
      deaths += untreatedDeaths;

      const treatedBeforeTotal = treatedAfterStart[sex].reduce((sum, row) => sum + row.reduce((inner, value) => inner + value, 0), 0);
      const treatedAfterTotal = treatedSurvivors.reduce((sum, row) => sum + row.reduce((inner, value) => inner + value, 0), 0);
      deaths += treatedBeforeTotal - treatedAfterTotal;

      nextUntreated[sex] = ageSurvivors(untreatedSurvivors);
      nextTreated[sex] = ageTreatedSurvivors(treatedSurvivors);
    }

    nextUntreated.male[0] += births.maleBirths;
    nextUntreated.female[0] += births.femaleBirths;

    let nextState = {
      untreated: nextUntreated,
      treated: nextTreated,
    };

    if (scenario.migration_mode === "on") {
      nextState = applyMigrationResidual(nextState, inputs.migration_residual[String(year)], scenario, year, maxAge);
    }

    untreated = nextState.untreated;
    treated = nextState.treated;

    const nextYear = year + 1;
    recordPopulationRows(populationRows, scenario, nextYear, untreated, treated);
    recordSummaryRow(summaryRows, scenario, nextYear, untreated, treated, births.totalBirths, deaths);
    snapshots[String(nextYear)] = buildSnapshot(untreated, treated);
  }

  return {
    populationRows,
    summaryRows,
    snapshots,
    survivalCurve: buildCohortSurvivalCurve(interventionAsset, scenario),
  };
}


export function buildPyramidSeries(result, year) {
  const snapshot = result.snapshots[String(year)];
  const ages = snapshot.untreated.male.map((_, age) => age);
  return {
    ages,
    male: snapshot.untreated.male.map((value, age) => value + snapshot.treatedByAge.male[age]),
    female: snapshot.untreated.female.map((value, age) => value + snapshot.treatedByAge.female[age]),
    treatedMale: snapshot.treatedByAge.male,
    treatedFemale: snapshot.treatedByAge.female,
  };
}


export function buildAgeDistributionSeries(result, year) {
  const snapshot = result.snapshots[String(year)];
  const ages = snapshot.untreated.male.map((_, age) => age);
  const untreated = ages.map((age) => {
    return snapshot.untreated.male[age] + snapshot.untreated.female[age];
  });
  const treated = ages.map((age) => {
    return snapshot.treatedByAge.male[age] + snapshot.treatedByAge.female[age];
  });

  return {
    ages,
    untreated,
    treated,
    total: ages.map((age) => untreated[age] + treated[age]),
  };
}


export function buildHeatmap(result) {
  const byYearAge = new Map();

  for (const row of result.populationRows) {
    const key = `${row.year}-${row.age}`;
    const entry = byYearAge.get(key) || { population: 0, treated: 0 };
    entry.population += row.population_count;
    entry.treated += row.treated_population_count;
    byYearAge.set(key, entry);
  }

  const years = [...new Set(result.populationRows.map((row) => row.year))].sort((a, b) => a - b);
  const ages = [...new Set(result.populationRows.map((row) => row.age))].sort((a, b) => a - b);
  const values = ages.map((age) => years.map((year) => {
    const entry = byYearAge.get(`${year}-${age}`) || { population: 0, treated: 0 };
    if (entry.population <= 0) {
      return 0;
    }
    return entry.treated / entry.population;
  }));

  return { years, ages, values };
}


export function buildLineSeries(result, key) {
  return {
    x: result.summaryRows.map((row) => row.year),
    y: result.summaryRows.map((row) => row[key]),
  };
}


export function rowsToCsv(rows) {
  if (!rows.length) {
    return "";
  }

  const headers = Object.keys(rows[0]);
  const lines = [headers.join(",")];

  for (const row of rows) {
    const values = headers.map((header) => {
      const value = row[header];
      if (value === null || value === undefined) {
        return "";
      }
      const text = `${value}`.replace(/"/g, "\"\"");
      return /[",\n]/.test(text) ? `"${text}"` : text;
    });
    lines.push(values.join(","));
  }

  return lines.join("\n");
}
