import fs from "node:fs";

import { projectScenario } from "../../dashboard/runtime.mjs";


const payloadPath = process.argv[2];
if (!payloadPath) {
  throw new Error("Expected payload path");
}

const payload = JSON.parse(fs.readFileSync(payloadPath, "utf8"));
const result = projectScenario(payload.inputs, payload.scenario, payload.interventionAsset);

process.stdout.write(JSON.stringify({
  populationRows: result.populationRows,
  summaryRows: result.summaryRows,
}));
