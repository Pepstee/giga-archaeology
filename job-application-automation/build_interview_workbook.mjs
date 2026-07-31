import fs from "node:fs/promises";
import {
  SpreadsheetFile,
  Workbook,
} from "/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const base = "/Users/admin/Documents/giga-user/job-application-automation/interview-preparation";
const outputDir = "/Users/admin/Documents/giga-user/outputs/interview-prep-2026-07-24";
const questions = JSON.parse(await fs.readFile(`${base}/questions.json`, "utf8"));
const categories = JSON.parse(await fs.readFile(`${base}/category_summary.json`, "utf8"));
const jobs = JSON.parse(await fs.readFile(`${base}/source_jobs.json`, "utf8"));

const wb = Workbook.create();
wb.comments.setSelf({ displayName: "Artiom Gutu" });

const navy = "#17324D";
const blue = "#245B8A";
const cyan = "#DCEEF8";
const pale = "#F5F8FB";
const gold = "#F4B942";
const green = "#DFF3E4";
const red = "#FBE2E2";
const grey = "#64748B";
const white = "#FFFFFF";

function titleBand(sheet, range, text) {
  sheet.getRange(range).merge();
  const cell = sheet.getRange(range.split(":")[0]);
  cell.values = [[text]];
  cell.format = {
    fill: navy,
    font: { bold: true, color: white, size: 18 },
    verticalAlignment: "center",
    horizontalAlignment: "left",
  };
  sheet.getRange(range).format.rowHeight = 34;
}

function styleHeader(range) {
  range.format = {
    fill: blue,
    font: { bold: true, color: white },
    verticalAlignment: "center",
    horizontalAlignment: "left",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: navy },
  };
  range.format.rowHeight = 30;
}

const plan = wb.worksheets.add("Flight Plan");
plan.showGridLines = false;
titleBand(plan, "A1:H1", "INTERVIEW PREPARATION — FIVE-HOUR FLIGHT PLAN");
plan.getRange("A3:H3").values = [[
  "Purpose",
  "Answer 100 questions aloud or in writing. Spend three minutes per question; use evidence, not invented competence.",
  null, null, null, null, null, null,
]];
plan.getRange("A3").format.font = { bold: true, color: navy };
plan.getRange("B3:H3").merge();
plan.getRange("A3:H3").format = { fill: cyan, wrapText: true, verticalAlignment: "center" };
plan.getRange("A3:H3").format.rowHeight = 46;

plan.getRange("A5:D5").values = [["Metric", "Value", "Target", "Interpretation"]];
styleHeader(plan.getRange("A5:D5"));
plan.getRange("A6:D10").values = [
  ["Total questions", null, 100, "Full flight pack"],
  ["Answered", null, 100, "Status = Answered"],
  ["Needs revision", null, 0, "Weak or incomplete evidence"],
  ["Minutes planned", null, 300, "Exactly five hours"],
  ["Completion", null, 1, "Share of questions answered"],
];
plan.getRange("B6").formulas = [["=COUNTA('Flight Questions'!$A$3:$A$102)"]];
plan.getRange("B7").formulas = [["=COUNTIF('Flight Questions'!$F$3:$F$102,\"Answered\")"]];
plan.getRange("B8").formulas = [["=COUNTIF('Flight Questions'!$F$3:$F$102,\"Needs revision\")"]];
plan.getRange("B9").formulas = [["=SUM('Flight Questions'!$E$3:$E$102)"]];
plan.getRange("B10").formulas = [["=IF(B6=0,0,B7/B6)"]];
plan.getRange("B10:C10").format.numberFormat = "0%";
plan.getRange("A6:D10").format.borders = {
  insideHorizontal: { style: "thin", color: "#D8E1EA" },
  bottom: { style: "thin", color: "#D8E1EA" },
};
plan.getRange("A6:A10").format.font = { bold: true, color: navy };

plan.getRange("A12:H12").values = [[
  "Block", "Minutes", "Question ranks", "Primary focus", "Break", "Output test", "If stuck", "Evidence rule",
]];
styleHeader(plan.getRange("A12:H12"));
plan.getRange("A13:H17").values = [
  [1, 60, "1–20", "Highest-frequency cross-role questions", "5 min", "One concrete answer per question", "Mark Needs revision and continue", "Name your exact action"],
  [2, 60, "21–40", "Python, APIs and data", "5 min", "Explain one design trade-off", "Sketch the system", "Do not claim code agents wrote"],
  [3, 60, "41–60", "Cloud, runtime and delivery", "10 min", "Diagnose aloud step by step", "State first three checks", "Separate research from production"],
  [4, 60, "61–80", "AI, agents and security", "5 min", "State deterministic boundary", "Use Market Aligner/orchestrator", "Disclose uncertainty"],
  [5, 60, "81–100", "Behavioural and customer-facing", "None", "Record a two-minute version", "Use Appco/tutoring/company", "Situation → action → result"],
];
plan.getRange("A13:H17").format = {
  fill: pale,
  wrapText: true,
  verticalAlignment: "top",
  borders: { preset: "inside", style: "thin", color: "#D8E1EA" },
};
plan.getRange("A13:H17").format.rowHeight = 50;

plan.getRange("A19:H19").merge();
plan.getRange("A19").values = [["ANSWER STANDARD"]];
plan.getRange("A19").format = { fill: gold, font: { bold: true, color: navy }, horizontalAlignment: "left" };
plan.getRange("A20:H24").values = [
  ["1", "Answer the question directly in the first sentence.", null, null, null, null, null, null],
  ["2", "Give one specific project or incident; avoid generic textbook prose.", null, null, null, null, null, null],
  ["3", "Separate what you designed/implemented from what AI agents generated.", null, null, null, null, null, null],
  ["4", "Name an observable result: test count, failure repaired, workflow completed, user outcome or limitation.", null, null, null, null, null, null],
  ["5", "End with the trade-off, limitation or lesson—not a promotional conclusion.", null, null, null, null, null, null],
];
for (let r = 20; r <= 24; r++) plan.getRange(`B${r}:H${r}`).merge();
plan.getRange("A20:H24").format = { wrapText: true, fill: "#FFF9E8" };
plan.getRange("A20:A24").format.font = { bold: true, color: navy };
plan.getRange("A1:H24").format.font.name = "Aptos";
plan.getRange("A1:H24").format.verticalAlignment = "center";
plan.getRange("A:A").format.columnWidth = 17;
plan.getRange("B:B").format.columnWidth = 19;
plan.getRange("C:C").format.columnWidth = 18;
plan.getRange("D:D").format.columnWidth = 29;
plan.getRange("E:E").format.columnWidth = 12;
plan.getRange("F:F").format.columnWidth = 29;
plan.getRange("G:G").format.columnWidth = 26;
plan.getRange("H:H").format.columnWidth = 28;
plan.freezePanes.freezeRows(1);

const flightQs = wb.worksheets.add("Flight Questions");
flightQs.showGridLines = false;
titleBand(flightQs, "A1:H1", "FLIGHT WORKSHEET — ANSWER FROM RANK 1 TO 100");
flightQs.getRange("A2:H2").values = [[
  "Rank", "Category", "Question", "Truthful evidence cue", "Minutes", "Status",
  "Your answer", "Follow-up / weakness",
]];
styleHeader(flightQs.getRange("A2:H2"));
const flightRows = questions.map(q => [
  q.rank, q.category, q.question, q.evidence_prompt, q.target_minutes, q.status,
  q.answer_notes, "",
]);
flightQs.getRange(`A3:H${flightRows.length + 2}`).values = flightRows;
flightQs.getRange(`A3:H${flightRows.length + 2}`).format = {
  wrapText: true,
  verticalAlignment: "top",
  borders: { insideHorizontal: { style: "thin", color: "#E2E8F0" } },
};
flightQs.getRange(`A3:A${flightRows.length + 2}`).format.font = { bold: true, color: navy };
flightQs.getRange(`E3:E${flightRows.length + 2}`).format.numberFormat = "0";
flightQs.getRange(`F3:F${flightRows.length + 2}`).dataValidation = {
  rule: { type: "list", values: ["Not started", "Drafted", "Answered", "Needs revision"] },
};
flightQs.getRange(`F3:F${flightRows.length + 2}`).conditionalFormats.add("containsText", {
  text: "Answered", format: { fill: green, font: { color: "#166534", bold: true } },
});
flightQs.getRange(`F3:F${flightRows.length + 2}`).conditionalFormats.add("containsText", {
  text: "Needs revision", format: { fill: red, font: { color: "#991B1B", bold: true } },
});
flightQs.getRange(`F3:F${flightRows.length + 2}`).conditionalFormats.add("containsText", {
  text: "Drafted", format: { fill: "#FFF1C2", font: { color: "#854D0E", bold: true } },
});
flightQs.tables.add(`A2:H${flightRows.length + 2}`, true, "FlightQuestionsTable");
flightQs.freezePanes.freezeRows(2);
flightQs.freezePanes.freezeColumns(3);
[7, 23, 58, 52, 10, 17, 68, 38].forEach((w, i) =>
  flightQs.getRangeByIndexes(0, i, flightRows.length + 2, 1).format.columnWidth = w
);
flightQs.getRange(`3:${flightRows.length + 2}`).format.rowHeight = 68;
flightQs.getRange("A1:H102").format.font.name = "Aptos";

const qs = wb.worksheets.add("Questions");
qs.showGridLines = false;
titleBand(qs, "A1:O1", "TOP 100 EMPLOYER INTERVIEW QUESTIONS — MARKET ALIGNER CORPUS");
const qHeaders = [
  "Rank", "Category", "Question", "What it tests", "Supporting jobs", "Corpus prevalence",
  "Top companies", "Example roles", "Source URLs", "Truthful evidence prompt",
  "Answer framework", "Target minutes", "Status", "Your answer / notes", "Follow-up weakness",
];
qs.getRange("A2:O2").values = [qHeaders];
styleHeader(qs.getRange("A2:O2"));
const qRows = questions.map(q => [
  q.rank, q.category, q.question, q.tests, q.supporting_jobs, q.prevalence,
  q.top_companies, q.example_roles, q.source_urls, q.evidence_prompt,
  q.answer_framework, q.target_minutes, q.status, q.answer_notes, "",
]);
qs.getRange(`A3:O${qRows.length + 2}`).values = qRows;
qs.getRange(`A3:O${qRows.length + 2}`).format = {
  wrapText: true,
  verticalAlignment: "top",
  borders: { insideHorizontal: { style: "thin", color: "#E2E8F0" } },
};
qs.getRange(`A3:A${qRows.length + 2}`).format.font = { bold: true, color: navy };
qs.getRange(`E3:E${qRows.length + 2}`).format.numberFormat = "0";
qs.getRange(`F3:F${qRows.length + 2}`).format.numberFormat = "0.0%";
qs.getRange(`L3:L${qRows.length + 2}`).format.numberFormat = "0";
qs.getRange(`M3:M${qRows.length + 2}`).dataValidation = {
  rule: { type: "list", values: ["Not started", "Drafted", "Answered", "Needs revision"] },
};
qs.getRange(`M3:M${qRows.length + 2}`).conditionalFormats.add("containsText", {
  text: "Answered", format: { fill: green, font: { color: "#166534", bold: true } },
});
qs.getRange(`M3:M${qRows.length + 2}`).conditionalFormats.add("containsText", {
  text: "Needs revision", format: { fill: red, font: { color: "#991B1B", bold: true } },
});
qs.getRange(`M3:M${qRows.length + 2}`).conditionalFormats.add("containsText", {
  text: "Drafted", format: { fill: "#FFF1C2", font: { color: "#854D0E", bold: true } },
});
qs.tables.add(`A2:O${qRows.length + 2}`, true, "InterviewQuestionsTable");
qs.freezePanes.freezeRows(2);
qs.freezePanes.freezeColumns(3);
const qWidths = [7, 23, 54, 27, 14, 15, 36, 42, 48, 54, 48, 13, 17, 58, 34];
qWidths.forEach((w, i) => qs.getRangeByIndexes(0, i, qRows.length + 2, 1).format.columnWidth = w);
qs.getRange(`3:${qRows.length + 2}`).format.rowHeight = 76;
qs.getRange("A1:O102").format.font.name = "Aptos";

const cat = wb.worksheets.add("Category Summary");
cat.showGridLines = false;
titleBand(cat, "A1:F1", "QUESTION COVERAGE BY INTERVIEW DOMAIN");
cat.getRange("A2:F2").values = [[
  "Category", "Questions", "Minutes", "Average supporting jobs", "Highest-ranked question", "Evidence boundary",
]];
styleHeader(cat.getRange("A2:F2"));
const catRows = categories.map(c => [
  c.category, c.question_count, c.minutes, c.avg_supporting_jobs, c.top_rank, c.evidence_boundary,
]);
cat.getRange(`A3:F${catRows.length + 2}`).values = catRows;
cat.getRange(`A3:F${catRows.length + 2}`).format = {
  wrapText: true, verticalAlignment: "top",
  borders: { insideHorizontal: { style: "thin", color: "#D8E1EA" } },
};
cat.getRange(`A3:A${catRows.length + 2}`).format.font = { bold: true, color: navy };
cat.tables.add(`A2:F${catRows.length + 2}`, true, "CategorySummaryTable");
cat.freezePanes.freezeRows(2);
[25, 13, 13, 24, 22, 90].forEach((w, i) => cat.getRangeByIndexes(0, i, catRows.length + 2, 1).format.columnWidth = w);
cat.getRange(`3:${catRows.length + 2}`).format.rowHeight = 64;

const sources = wb.worksheets.add("Source Jobs");
sources.showGridLines = false;
titleBand(sources, "A1:I1", "548 PROCESSED VACANCIES USED AS QUESTION EVIDENCE");
sources.getRange("A2:I2").values = [[
  "Company", "Role", "Mapped career", "Fit", "Opportunity", "Final score", "Location", "Source URL", "Why it fits / evidence gap",
]];
styleHeader(sources.getRange("A2:I2"));
const jobRows = jobs.map(j => [
  j.company, j.job_title, j.mapped_career, j.fit, j.opportunity, j.final, j.location, j.url, j.why_it_fits,
]);
sources.getRange(`A3:I${jobRows.length + 2}`).values = jobRows;
sources.getRange(`A3:I${jobRows.length + 2}`).format = {
  wrapText: true, verticalAlignment: "top",
  borders: { insideHorizontal: { style: "thin", color: "#E2E8F0" } },
};
sources.getRange(`D3:E${jobRows.length + 2}`).format.numberFormat = "0.0%";
sources.getRange(`F3:F${jobRows.length + 2}`).format.numberFormat = "0.0";
sources.tables.add(`A2:I${jobRows.length + 2}`, true, "SourceJobsTable");
sources.freezePanes.freezeRows(2);
sources.freezePanes.freezeColumns(2);
[25, 42, 27, 11, 13, 13, 30, 55, 85].forEach((w, i) => sources.getRangeByIndexes(0, i, jobRows.length + 2, 1).format.columnWidth = w);
sources.getRange(`3:${Math.min(jobRows.length + 2, 550)}`).format.rowHeight = 58;

await fs.mkdir(outputDir, { recursive: true });
const exported = await SpreadsheetFile.exportXlsx(wb);
const outputPath = `${outputDir}/Artiom_Gutu_5_Hour_Interview_Flight_Pack.xlsx`;
await exported.save(outputPath);

for (const [sheetName, range, file] of [
  ["Flight Plan", "A1:H24", "preview-flight-plan.png"],
  ["Flight Questions", "A1:H12", "preview-flight-questions.png"],
  ["Questions", "A1:O12", "preview-questions.png"],
  ["Category Summary", `A1:F${catRows.length + 2}`, "preview-categories.png"],
  ["Source Jobs", "A1:I12", "preview-source-jobs.png"],
]) {
  const blob = await wb.render({ sheetName, range, scale: 1.2, format: "png" });
  await fs.writeFile(`${outputDir}/${file}`, new Uint8Array(await blob.arrayBuffer()));
}

const check = await wb.inspect({
  kind: "table",
  range: "Flight Questions!A1:H12",
  include: "values,formulas",
  tableMaxRows: 12,
  tableMaxCols: 8,
});
await fs.writeFile(`${outputDir}/qa-inspect.ndjson`, check.ndjson);
const errors = await wb.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
await fs.writeFile(`${outputDir}/qa-errors.ndjson`, errors.ndjson);
console.log(outputPath);
