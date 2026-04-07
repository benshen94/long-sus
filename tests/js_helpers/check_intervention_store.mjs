import fs from "node:fs";

import { createInterventionStore } from "../../dashboard/interventions.mjs";


const payloadPath = process.argv[2];
if (!payloadPath) {
  throw new Error("Expected payload path");
}

const payload = JSON.parse(fs.readFileSync(payloadPath, "utf8"));

let fetchCount = 0;
let lastUrl = "";

const fetchJson = async (url) => {
  fetchCount += 1;
  lastUrl = url;
  return {
    target: "eta",
    factor: 0.8,
    hetero_mode: "off",
    start_ages: payload.demography.ages,
    ages: payload.demography.ages,
    annual_hazard_multiplier: payload.demography.ages.map(() => payload.demography.ages.map(() => 1)),
    baseline_survival: payload.demography.ages.map(() => 1).concat([1]),
    survival_by_start_age: payload.demography.ages.map(() => payload.demography.ages.map(() => 1).concat([1])),
  };
};

const store = createInterventionStore({
  manifest: payload.manifest,
  demography: payload.demography,
  analyticPresets: payload.analyticPresets,
  fetchJson,
});

await store.getAsset({
  target: "eta",
  factor: 0.8,
  branch: "sr",
  hetero_mode: "off",
  launch_year: 2024,
  analytic_preset_id: null,
});
await store.getAsset({
  target: "eta",
  factor: 0.8,
  branch: "sr",
  hetero_mode: "off",
  launch_year: 2024,
  analytic_preset_id: null,
});

const srFetchCount = fetchCount;

await store.getAsset({
  target: "eta",
  factor: 0.8,
  branch: "analytic_arm",
  hetero_mode: "off",
  launch_year: 2024,
  analytic_preset_id: "usa_period_2019_both_hazard",
});

process.stdout.write(JSON.stringify({
  fetchCount,
  srUrl: lastUrl,
  analyticFetchCount: fetchCount,
  srFetchCount,
}));
