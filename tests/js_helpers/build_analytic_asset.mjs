import fs from "node:fs";

import { buildAnalyticInterventionAsset } from "../../dashboard/interventions.mjs";


const payloadPath = process.argv[2];
if (!payloadPath) {
  throw new Error("Expected payload path");
}

const payload = JSON.parse(fs.readFileSync(payloadPath, "utf8"));
const asset = buildAnalyticInterventionAsset({
  demography: payload.demography,
  target: payload.target,
  factor: payload.factor,
  launchYear: payload.launchYear,
  analyticPreset: payload.analyticPreset,
});

process.stdout.write(JSON.stringify(asset));
