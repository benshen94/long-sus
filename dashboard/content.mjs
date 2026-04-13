const PRESET_COPY = {
  no_one: "No one is treated. This is the untreated baseline for comparison.",
  everyone: "Everyone is treated as soon as the intervention launches.",
  only_elderly_65plus: "Treat 100% of ages 65+.",
  "50pct_elderly_65plus": "Treat 50% of ages 65+.",
  "30pct_middle_40_64_plus_70pct_elderly_65plus": "Treat 30% of ages 40-64 and 70% of ages 65+.",
  half_population_adult_band: "Treat 50% of adults ages 20+.",
  prescription_bands_absolute: "Use the paper-style age bands, with the targeted share starting as soon as people reach the band edge.",
  prescription_bands_equal_probabilities: "Use the paper-style age bands, but spread starts across the band with one constant yearly chance.",
  prescription_bands_uniform_start_age: "Use the paper-style age bands, but tune yearly chances so realized start ages are uniform across the band.",
  threshold_age_60_all_eligible: "Treat 100% of people from age 60 onward. People already 60+ start at launch, and younger cohorts start when they first reach age 60.",
  rollout_threshold_linear: "Treat people from age 60 onward, but let annual take-up rise over calendar time with a straight-line popularity ramp.",
  rollout_threshold_logistic: "Treat people from age 60 onward, but let annual take-up follow an S-curve with a slow start, faster middle, and later saturation.",
};

const UPTAKE_MODE_COPY = {
  threshold: {
    title: "Threshold",
    short: "One eligibility age plus one fixed start share.",
    description: "Threshold uses one cutoff age plus one fixed treated share. At launch, that share of people already at or above the threshold starts. Later, the same share starts when each cohort first reaches the threshold age, and the untreated remainder do not catch up later.",
  },
  banded: {
    title: "Age bands",
    short: "Different treated shares for different age ranges.",
    description: "Age bands gives each age range its own treated share. You can keep starts immediate at the band edge, or spread them across the band with one of the within-band start rules.",
  },
  rollout: {
    title: "Rollout",
    short: "Eligibility by age, adoption by calendar-time popularity.",
    description: "Rollout keeps one eligibility age, but the annual chance of starting gets stronger after launch as the drug becomes more popular. Untreated eligible people keep getting another yearly chance to start, and once they start they stay on treatment.",
  },
};

const START_RULE_COPY = {
  absolute: "Everyone in the targeted share starts at the lower band edge, or immediately at launch if already inside that band.",
  equal_probabilities: "Every untreated person inside the band faces the same yearly chance to start while they remain in that age range.",
  uniform_start_age: "Yearly start chances are tuned so realized start ages end up spread evenly across the band.",
};

const TARGET_COPY = {
  eta: {
    title: "Slowing age (eta)",
    short: "The post-treatment rate of aging becomes smaller.",
    description: "Eta interventions reduce the rate of aging, or damage production, after treatment starts.",
    note: "Smaller factors mean stronger slowing.",
  },
  eta_shift: {
    title: "Rejuvenation (eta shift)",
    short: "Eta moves immediately at treatment start.",
    description: "Rolling back the clock - eta-shift interventions apply an immediate multiplicative change to eta at treatment start.",
    note: "In this dashboard, eta_new = eta_old * factor, so larger factors mean a larger immediate shift.",
  },
  Xc: {
    title: "Increasing robustness (Xc)",
    short: "The survival curve becomes more rectangular.",
    description: "Rectangularization - Xc interventions compress deaths into a narrower late-life window.",
    note: "Larger factors mean stronger robustness and more rectangularization of the survival curve.",
  },
};


function formatPercent(value) {
  return `${Math.round(Number(value) * 100)}%`;
}


function formatFactor(value) {
  return `${Number(value).toFixed(2)}x`;
}


export function describePreset(preset) {
  if (!preset) {
    return "";
  }

  if (PRESET_COPY[preset.id]) {
    return PRESET_COPY[preset.id];
  }

  if (preset.description) {
    return preset.description;
  }

  return "Preset description unavailable.";
}


export function describeUptakeMode(mode) {
  return UPTAKE_MODE_COPY[mode]?.description || "";
}


export function describeRolloutCurve(curve) {
  if (curve === "logistic") {
    return "Logistic rollout: annual take-up follows an S-curve with a slower start, faster middle, and later saturation.";
  }
  return "Linear rollout: annual take-up rises in a straight line from the launch-year chance to the long-run cap.";
}


export function explainScenarioStrategy(scenario) {
  if (!scenario) {
    return "";
  }

  if (scenario.uptake_mode === "threshold") {
    return `Threshold age ${scenario.threshold_age}. ${formatPercent(scenario.threshold_probability)} start when they first become eligible, and no one else gets another chance later.`;
  }

  if (scenario.uptake_mode === "rollout") {
    const base = `Eligibility starts at age ${scenario.threshold_age}. Untreated eligible people face a ${formatPercent(scenario.rollout_launch_probability)} annual start chance at launch, rising toward ${formatPercent(scenario.rollout_max_probability)} as popularity grows.`;
    if (scenario.rollout_curve === "logistic") {
      return `${base} The curve uses an S-shape with takeoff around ${scenario.rollout_takeoff_years} years after launch.`;
    }
    return `${base} The curve ramps linearly and reaches its cap after ${scenario.rollout_ramp_years} years.`;
  }

  return START_RULE_COPY[scenario.start_rule_within_band] || "";
}


function currentScenarioRows(context) {
  const target = TARGET_COPY[context.activeScenario.target] || null;
  const rows = [
    ["Area", context.countryLabel],
    ["Strategy", UPTAKE_MODE_COPY[context.activeScenario.uptake_mode]?.title || context.activeScenario.uptake_mode],
    ["Launch year", `${context.activeScenario.launch_year}`],
    ["Projection end year", `${context.activeScenario.projection_end_year}`],
    ["Target", target ? `${target.title} (${formatFactor(context.activeScenario.factor)})` : "No intervention target"],
    ["Analytic preset", context.analyticPresetLabel || "Default preset"],
  ];

  if (context.activeScenario.uptake_mode === "threshold") {
    rows.push(["Eligibility", `Ages ${context.activeScenario.threshold_age}+`]);
    rows.push(["Start share", formatPercent(context.activeScenario.threshold_probability)]);
  } else if (context.activeScenario.uptake_mode === "rollout") {
    rows.push(["Eligibility", `Ages ${context.activeScenario.threshold_age}+`]);
    rows.push(["Launch-year annual chance", formatPercent(context.activeScenario.rollout_launch_probability)]);
    rows.push(["Long-run annual cap", formatPercent(context.activeScenario.rollout_max_probability)]);
    rows.push(["Curve shape", context.activeScenario.rollout_curve === "logistic" ? "Logistic S-curve" : "Linear ramp"]);
    rows.push([
      "Timing",
      context.activeScenario.rollout_curve === "logistic"
        ? `Takeoff around year ${context.activeScenario.rollout_takeoff_years}`
        : `Cap reached after ${context.activeScenario.rollout_ramp_years} years`,
    ]);
  } else {
    rows.push(["Band rule", START_RULE_COPY[context.activeScenario.start_rule_within_band] || ""]);
  }

  return rows
    .map(([label, value]) => {
      return `
        <div class="methods-stat-row">
          <dt>${label}</dt>
          <dd>${value}</dd>
        </div>
      `;
    })
    .join("");
}


function methodsNav() {
  const items = [
    ["inputs", "What goes in"],
    ["projection", "Projection loop"],
    ["biology", "Intervention biology"],
    ["rollout", "Rollout rules"],
    ["outputs", "Read the outputs"],
    ["current", "Current scenario"],
  ];

  return items
    .map(([target, label]) => `<a class="methods-chip" href="#methods-${target}">${label}</a>`)
    .join("");
}


function methodsSection(id, eyebrow, title, lead, body, technicalNote = "") {
  return `
    <section class="methods-section" id="methods-${id}">
      <div class="methods-section-copy">
        <p class="eyebrow">${eyebrow}</p>
        <h3>${title}</h3>
        <p class="methods-lead">${lead}</p>
        ${body}
        ${technicalNote}
      </div>
    </section>
  `;
}


export function renderMethodsView(container, context) {
  if (!container) {
    return;
  }

  const target = TARGET_COPY[context.activeScenario.target] || null;
  const summary = context.activeSummary || null;
  const currentScenarioNote = summary
    ? `
      <p class="methods-lead">
        In ${summary.year}, the active scenario projects ${summary.total_population.toLocaleString(undefined, { maximumFractionDigits: 0 })}
        total people, with ${formatPercent(summary.treated_share)} treated and ${formatPercent(summary.old_age_share_65_plus)} age 65+.
      </p>
    `
    : "";
  const timingNote = context.activeScenario.uptake_mode === "rollout"
    ? describeRolloutCurve(context.activeScenario.rollout_curve)
    : context.activeScenario.uptake_mode === "banded"
      ? "The within-band start rule changes when cohorts enter treatment even when final treated shares stay the same."
      : "Threshold timing is simple: the entire dynamic comes from one eligibility age and one fixed start share.";

  const methodsMarkup = `
    <article class="methods-stage-inner">
      <header class="methods-hero">
        <div class="methods-hero-copy">
          <p class="eyebrow">Methods</p>
          <h2>How the dashboard turns a treatment rule into a population forecast.</h2>
          <p class="methods-lead">The browser combines demography with an intervention treatment-start rule.</p>
          <p class="methods-lead">The intervention shape comes from the SR model.</p>
        </div>
      </header>

      <nav class="methods-nav" aria-label="Methods sections">
        ${methodsNav()}
      </nav>

      ${methodsSection(
        "inputs",
        "Inputs",
        "What goes in",
        "The population backbone comes from WPP demography. You can include or remove migration. The intervention shape comes from the SR model.",
        `
          <div class="methods-grid">
            <div class="methods-card">
              <h4>Demography</h4>
              <ul class="methods-list">
                <li>Population by age and sex for each supported year.</li>
                <li>Mortality by age and sex.</li>
                <li>Fertility by maternal age and sex ratio at birth.</li>
                <li>Migration residuals that close the gap to the next WPP year.</li>
              </ul>
            </div>
            <div class="methods-card">
              <h4>Intervention surface</h4>
              <ul class="methods-list">
                <li>One hazard multiplier row for each possible treatment start age.</li>
                <li>The analytic arm builds these rows on demand from a named hazard-fit preset.</li>
                <li>The legacy SR branch uses stored surfaces instead.</li>
              </ul>
            </div>
          </div>
        `,
      )}

      ${methodsSection(
        "projection",
        "Projection loop",
        "How projection works",
        "Each year, the browser decides who starts treatment, applies survival, ages survivors forward, adds births, and optionally adds migration.",
        `
          <div class="methods-flow">
            <div class="flow-step"><span>1</span><strong>Start</strong><p>Apply the scenario rule to untreated people who are eligible this year.</p></div>
            <div class="flow-step"><span>2</span><strong>Survive</strong><p>Untreated people use baseline mortality. Treated people use the modified mortality rate according to the SR model.</p></div>
            <div class="flow-step"><span>3</span><strong>Age</strong><p>Survivors age by one year. People already in the oldest age group stay in that oldest age group instead of leaving the model.</p></div>
            <div class="flow-step"><span>4</span><strong>Births + migration</strong><p>Births come from fertility. If migration is turned on, the browser also applies the WPP migration residual.</p></div>
          </div>
        `,
        `
          <details class="methods-detail">
            <summary>Technical note</summary>
            <p>
              The code uses explicit vector and tensor updates instead of materializing one giant Leslie matrix,
              but the transition is still Leslie-equivalent. Treated people are tracked in a start-age by attained-age grid,
              which is why timing of treatment start matters.
            </p>
          </details>
        `,
      )}

      ${methodsSection(
        "biology",
        "Biology",
        "Intervention biology",
        "The dashboard separates the treatment-start rule from the intervention biology. That is what lets two scenarios share the same eta or Xc factor but still age the population differently.",
        `
          <div class="methods-grid">
            <div class="methods-card">
              <h4>${TARGET_COPY.eta.title}</h4>
              <p>${TARGET_COPY.eta.description}</p>
              <p class="methods-footnote">${TARGET_COPY.eta.note}</p>
            </div>
            <div class="methods-card">
              <h4>${TARGET_COPY.eta_shift.title}</h4>
              <p>${TARGET_COPY.eta_shift.description}</p>
              <p class="methods-footnote">${TARGET_COPY.eta_shift.note}</p>
            </div>
            <div class="methods-card">
              <h4>${TARGET_COPY.Xc.title}</h4>
              <p>${TARGET_COPY.Xc.description}</p>
              <p class="methods-footnote">${TARGET_COPY.Xc.note}</p>
            </div>
          </div>
        `,
        `
          <details class="methods-detail">
            <summary>Technical note</summary>
            <p class="methods-math">
              The analytic arm starts from h(t) proportional to exp[-(Xc / epsilon)(beta - eta t)] and then
              changes eta, eta-shift, or Xc only after treatment start.
            </p>
          </details>
        `,
      )}

      ${methodsSection(
        "rollout",
        "Scenarios",
        "Rollout rules",
        "The dashboard exposes three distinct ways to decide who starts treatment. Threshold and age bands are age-first rules. Rollout is a popularity-over-time rule layered on top of age eligibility.",
        `
          <div class="methods-grid methods-grid-wide">
            <div class="methods-card methods-diagram-card">
              <h4>${UPTAKE_MODE_COPY.threshold.title}</h4>
              <p>${UPTAKE_MODE_COPY.threshold.short}</p>
              <div class="scenario-diagram threshold-diagram" aria-hidden="true">
                <span class="diagram-bar diagram-muted"></span>
                <span class="diagram-bar diagram-active"></span>
              </div>
              <p class="methods-footnote">One age cutoff. One fixed start share.</p>
            </div>
            <div class="methods-card methods-diagram-card">
              <h4>${UPTAKE_MODE_COPY.banded.title}</h4>
              <p>${UPTAKE_MODE_COPY.banded.short}</p>
              <div class="scenario-diagram banded-diagram" aria-hidden="true">
                <span class="diagram-band diagram-band-soft"></span>
                <span class="diagram-band diagram-band-mid"></span>
                <span class="diagram-band diagram-band-strong"></span>
              </div>
              <p class="methods-footnote">Different age ranges can have different treated shares and start rules.</p>
            </div>
            <div class="methods-card methods-diagram-card">
              <h4>${UPTAKE_MODE_COPY.rollout.title}</h4>
              <p>${UPTAKE_MODE_COPY.rollout.short}</p>
              <div class="scenario-diagram rollout-diagram" aria-hidden="true">
                <span class="diagram-axis"></span>
                <span class="diagram-curve"></span>
              </div>
              <p class="methods-footnote">${timingNote}</p>
              <ul class="methods-list">
                <li>Linear rollout: annual take-up rises in a straight line from the launch-year chance to the long-run cap.</li>
                <li>Logistic rollout: annual take-up follows an S-curve, slower at first, faster in the middle, then saturating later.</li>
              </ul>
            </div>
          </div>
        `,
        `
          <details class="methods-detail">
            <summary>Technical note</summary>
            <p class="methods-math">
              Linear rollout uses p(y) = p0 + (pmax - p0) min(y / T, 1). Logistic rollout uses
              L(y) = 1 / (1 + exp(-0.5(y - m))) and rescales it so p(0) = p0 and p(y) approaches pmax.
            </p>
          </details>
        `,
      )}

      ${methodsSection(
        "outputs",
        "Outputs",
        "How to read the outputs",
        "Each plot answers a different question. The heatmap is the bridge between the scenario rule and the demographic result.",
        `
          <div class="methods-grid">
            <div class="methods-card">
              <h4>Population view</h4>
              <p>The age distribution or pyramid shows where the intervention reshapes the age structure.</p>
            </div>
            <div class="methods-card">
              <h4>Total population</h4>
              <p>Checks whether the intervention mostly changes headcount or mostly changes age structure.</p>
            </div>
            <div class="methods-card">
              <h4>Population share</h4>
              <p>Tracks how much of the population is at or above the chosen age cutoff over time.</p>
            </div>
            <div class="methods-card">
              <h4>Treated-share heatmap</h4>
              <p>Shows which age-year cells are treated. This is usually the fastest way to explain why two scenarios diverge.</p>
            </div>
            <div class="methods-card">
              <h4>Survival curves</h4>
              <p>Compare scenario survival curve to baseline.</p>
            </div>
          </div>
        `,
      )}

      ${methodsSection(
        "current",
        "Current run",
        "Current scenario",
        explainScenarioStrategy(context.activeScenario),
        `
          ${currentScenarioNote}
          <dl class="methods-stats">
            ${currentScenarioRows(context)}
          </dl>
          <div class="methods-card methods-card-accent">
            <h4>Why timing matters here</h4>
            <p>
              ${target ? target.description : "The active scenario is an untreated baseline."}
              The intervention rule determines when cohorts enter treatment, so two runs with the same biology can still produce different heatmaps and different old-age shares.
            </p>
            <p class="methods-footnote">${timingNote}</p>
          </div>
        `,
      )}
    </article>
  `;

  container.innerHTML = methodsMarkup;
}
