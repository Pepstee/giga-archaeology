import fs from "node:fs/promises";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const root = "/Users/admin/Documents/giga-user";
const outDir = `${root}/outputs/hyun_results_20260720`;
const scoredPath = `${root}/market-aligner/skeleton/data/bulk_500/jobs_scored_terra.jsonl`;
const audit = JSON.parse(await fs.readFile(`${outDir}/frequency_audit.json`, "utf8"));
const jobs = (await fs.readFile(scoredPath, "utf8")).trim().split("\n").map(JSON.parse);
jobs.sort((a, b) => (b.final ?? -1) - (a.final ?? -1));

const wb = Workbook.create();
const NAVY = "#17324D", BLUE = "#2F75B5", PALE = "#DDEBF7", GREEN = "#E2F0D9";
const ORANGE = "#FCE4D6", GREY = "#E7E6E6", WHITE = "#FFFFFF", TEXT = "#1F2937";

function colName(n) {
  let out = "";
  while (n > 0) { n--; out = String.fromCharCode(65 + (n % 26)) + out; n = Math.floor(n / 26); }
  return out;
}

function writeTable(sheet, headers, rows, tableName, widths = []) {
  const matrix = [headers, ...rows];
  const end = `${colName(headers.length)}${matrix.length}`;
  sheet.getRange(`A1:${end}`).writeValues(matrix);
  sheet.getRange(`A1:${colName(headers.length)}1`).format = {
    fill: NAVY, font: { bold: true, color: WHITE }, wrapText: true,
    verticalAlignment: "center", borders: { preset: "all", style: "thin", color: "#B4C6E7" },
  };
  sheet.getRange(`A2:${end}`).format = {
    font: { color: TEXT }, verticalAlignment: "top",
    borders: { preset: "all", style: "thin", color: "#D9E2F3" },
  };
  sheet.tables.add(`A1:${end}`, true, tableName).style = "TableStyleMedium2";
  sheet.freezePanes.freezeRows(1);
  sheet.showGridLines = false;
  widths.forEach((w, i) => { if (w) sheet.getRange(`${colName(i + 1)}:${colName(i + 1)}`).format.columnWidth = w; });
  return end;
}

// Summary / read-me sheet.
const summary = wb.worksheets.add("요약_Summary");
summary.showGridLines = false;
summary.getRange("A1:H1").merge();
summary.getRange("A1").values = [["Hyun — 채용시장 정렬 결과 / Market Alignment Results"]];
summary.getRange("A1:H1").format = { fill: NAVY, font: { bold: true, color: WHITE, size: 18 }, rowHeight: 34 };
summary.getRange("A3:B10").writeValues([
  ["지표 / Metric", "값 / Value"],
  ["LLM 구조화·평가 완료", audit.summary.scored_jobs],
  ["신입 지원 가능으로 분류", audit.summary.eligible_entry_level_jobs],
  ["경력직으로 분류", audit.summary.non_entry_jobs],
  ["경력 수준 불명확", audit.summary.unclear_entry_status],
  ["구조화된 툴 요구사항 보유 (신입)", audit.summary.eligible_with_structured_tools],
  ["광의 요구역량 보유 (신입)", audit.summary.eligible_with_broader_requirements],
  ["추출 실패", 1],
]);
summary.getRange("A3:B3").format = { fill: NAVY, font: { bold: true, color: WHITE } };
summary.getRange("A4:B10").format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
summary.getRange("D3:H3").merge(); summary.getRange("D3").values = [["먼저 읽어주세요 / Read first"]];
summary.getRange("D3:H3").format = { fill: BLUE, font: { bold: true, color: WHITE } };
summary.getRange("D4:H10").merge();
summary.getRange("D4").values = [[
  "이 결과는 1,331개 공고를 동일 기준으로 비교한 상대 순위입니다. 채용 확률이 아닙니다. " +
  "meta.calibrated=false 상태이므로 30개 공고에 대한 사람 검토 후 점수 보정이 필요합니다. " +
  "툴 빈도와 광의 요구역량은 신입(entry_level=true) 291개 공고만을 분모로 하며, 같은 공고 안의 같은 항목은 한 번만 셉니다."
]];
summary.getRange("D4:H10").format = { fill: PALE, wrapText: true, verticalAlignment: "top", font: { color: TEXT } };
summary.getRange("A12:H12").merge(); summary.getRange("A12").values = [["시트 안내 / Workbook guide"]];
summary.getRange("A12:H12").format = { fill: NAVY, font: { bold: true, color: WHITE } };
summary.getRange("A13:H19").writeValues([
  ["상위공고_TopJobs", "신입으로 분류된 공고 중 최종점수 상위 50개", null, null, null, null, null, null],
  ["분야순위_Fields", "전체 분야별 기회·적합도 요약", null, null, null, null, null, null],
  ["툴빈도_Tools", "구체적인 소프트웨어/도구 요구 빈도 — 별칭 교정 완료", null, null, null, null, null, null],
  ["요구역량_Requirements", "직무지식·방법·툴을 포함한 광의 요구역량 빈도", null, null, null, null, null, null],
  ["학습격차_LearningGaps", "광의 요구역량 중 프로필에 보유 증거가 없는 항목", null, null, null, null, null, null],
  ["전체공고_AllJobs", "평가된 1,331개 공고 전체", null, null, null, null, null, null],
  ["방법론_Method", "집계법, 제한사항, 별칭 교정 내역", null, null, null, null, null, null],
]);
summary.getRange("A13:A19").format = { fill: PALE, font: { bold: true, color: NAVY } };
summary.getRange("A13:H19").format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
summary.getRange("A:A").format.columnWidth = 28; summary.getRange("B:B").format.columnWidth = 18;
for (const c of ["D","E","F","G","H"]) summary.getRange(`${c}:${c}`).format.columnWidth = 16;
summary.freezePanes.freezeRows(1);

const topEligible = jobs.filter(j => j.entry_level === true).slice(0, 50);
const jobHeaders = ["rank","final","fit","opportunity","career","title","company","board","remote","site_intensity","required_software","skills_to_learn","confidence","url"];
const jobRows = topEligible.map((j, i) => [i+1,j.final,j.fit,j.opportunity,j.mapped_career,j.job_title,j.company,j.board,j.remote_flag,j.site_intensity,(j.required_software||[]).join(", "),(j.skills_to_learn||[]).join(", "),j.extraction_confidence,j.url]);
const top = wb.worksheets.add("상위공고_TopJobs");
writeTable(top, jobHeaders, jobRows, "TopJobsTable", [7,10,10,12,18,42,24,12,10,13,30,50,11,45]);
top.getRange(`B2:D${jobRows.length+1}`).format.numberFormat = "0.00";
top.getRange(`B2:B${jobRows.length+1}`).conditionalFormats.addColorScale({ minColor: "#F8696B", midColor: "#FFEB84", maxColor: "#63BE7B" });

const fields = [
  ["Spatial_VMD",1.993,163,41,0.5332],["3D_Generalist",1.6735,86,43,0.4422],["UX_UI",1.5611,413,66,0.3713],
  ["Motion_Graphic",1.4642,288,62,0.3534],["Exhibition",1.1619,21,8,0.5288],["ArchViz",0.863,9,5,0.4816],
  ["Brand_Space",0.649,53,3,0.4682],["other",0.6412,274,57,0.1579],["XR_Spatial",0.2819,5,2,0.2566],
  ["Environment_Art",0.25,7,2,0.2276],["Technical_Artist",0.1579,12,2,0.1437],
];
const fieldSheet = wb.worksheets.add("분야순위_Fields");
writeTable(fieldSheet, ["career","field_score","all_jobs","entry_level_jobs","median_fit"], fields, "FieldsTable", [22,14,12,18,14]);
fieldSheet.getRange("B2:B12").conditionalFormats.addDataBar({ color: BLUE, gradient: true });

function frequencySheet(name, rows, tableName, note) {
  const sheet = wb.worksheets.add(name);
  sheet.getRange("A1:F1").merge(); sheet.getRange("A1").values = [[note]];
  sheet.getRange("A1:F1").format = { fill: ORANGE, font: { bold: true, color: TEXT }, wrapText: true, rowHeight: 32 };
  const headers = ["requirement","frequency","pct_of_291","top_fields","owned_or_reported","raw_forms"];
  const values = rows.map(r => [r.requirement,r.frequency,r.pct_of_eligible_jobs,r.top_fields,r.owned_or_reported ? "Yes" : "No",r.raw_forms]);
  sheet.getRange(`A3:F${values.length+3}`).writeValues([headers, ...values]);
  sheet.getRange("A3:F3").format = { fill: NAVY, font: { bold: true, color: WHITE }, wrapText: true };
  sheet.getRange(`A4:F${values.length+3}`).format = { borders: { preset: "all", style: "thin", color: "#D9E2F3" }, verticalAlignment: "top" };
  sheet.tables.add(`A3:F${values.length+3}`, true, tableName).style = "TableStyleMedium2";
  sheet.freezePanes.freezeRows(3); sheet.showGridLines = false;
  [28,12,14,38,18,42].forEach((w, i) => sheet.getRange(`${colName(i+1)}:${colName(i+1)}`).format.columnWidth = w);
  sheet.getRange(`C4:C${values.length+3}`).format.numberFormat = "0.0";
  sheet.getRange(`B4:B${values.length+3}`).conditionalFormats.addDataBar({ color: BLUE, gradient: true });
  sheet.getRange(`E4:E${values.length+3}`).conditionalFormats.addCustom('=E4="Yes"', { fill: GREEN });
}

frequencySheet("툴빈도_Tools", audit.tool_prevalence, "ToolsFrequencyTable",
  "구체적 도구(required_software)만 집계합니다. 291개 신입 공고 기준, 공고당 1회. 모델 표기 드리프트(예: adobexd/adobe_xd)는 교정했습니다.");
frequencySheet("요구역량_Requirements", audit.requirement_prevalence, "RequirementsFrequencyTable",
  "skills_to_learn에서 추출된 광의 요구역량입니다. 도구뿐 아니라 방법론·직무지식도 포함합니다. 291개 신입 공고 기준, 공고당 1회.");
frequencySheet("학습격차_LearningGaps", audit.learning_gap_prevalence, "LearningGapsTable",
  "광의 요구역량에서 Hyun 프로필의 자기보고 보유 도구 6개를 제외했습니다. '보유 증거 없음'은 '능력 없음'이 아니며 검증 대상입니다.");

const allHeaders = ["final","fit","opportunity","entry_level","career","title","company","board","remote","site_intensity","required_software","skills_to_learn","confidence","why_it_fits","url"];
const allRows = jobs.map(j => [j.final,j.fit,j.opportunity,j.entry_level,j.mapped_career,j.job_title,j.company,j.board,j.remote_flag,j.site_intensity,(j.required_software||[]).join(", "),(j.skills_to_learn||[]).join(", "),j.extraction_confidence,j.why_it_fits,j.url]);
const all = wb.worksheets.add("전체공고_AllJobs");
writeTable(all, allHeaders, allRows, "AllJobsTable", [10,10,12,12,18,42,24,12,10,13,30,50,11,60,45]);
all.getRange(`A2:C${allRows.length+1}`).format.numberFormat = "0.00";

const method = wb.worksheets.add("방법론_Method");
writeTable(method, ["항목 / Item","설명 / Explanation"], [
  ["분모", "entry_level=true로 명시 분류된 291개 공고"],
  ["빈도 계산", "정규화된 항목별로 공고당 최대 1회"],
  ["툴 빈도", "required_software 필드만 사용 — 구체적 소프트웨어/도구"],
  ["광의 요구역량", "skills_to_learn 필드 사용 — 도구, 방법론, 직무지식 포함"],
  ["학습격차", "광의 요구역량에서 프로필의 tools_self_reported 6개를 제외"],
  ["보유 도구", "rhino, max3ds, revit, photoshop, illustrator, lumion — 숙련도 증명이 아닌 자기보고"],
  ["별칭 교정", "adobexd→adobe_xd; adobe_after_effects→aftereffects; premierepro/adobe_premiere_pro→premiere; substancepainter→substance_painter; stablediffusion→stable_diffusion; veo3→veo 등"],
  ["보존성", "원본 JSONL과 기존 XLSX는 수정하지 않았습니다. 교정은 이 전달본에만 적용됩니다."],
  ["점수 제한", "meta.calibrated=false. final/fit/opportunity는 상대 비교 점수이며 채용 확률이 아닙니다."],
  ["품질 제한", "1,332개 시도 중 1개 추출 실패. entry_level 불명확 27개는 빈도 분모에서 제외."],
  ["다음 검증", "상위 30개 공고를 사람이 검토해 지원 가능성·관심·생활제약을 보정한 뒤 점수 캘리브레이션"],
], "MethodTable", [24,100]);
method.getRange("B:B").format.wrapText = true;

const outPath = `${outDir}/Hyun_Market_Alignment_Results.xlsx`;
await (await SpreadsheetFile.exportXlsx(wb)).save(outPath);

const inspect = await wb.inspect({ kind: "workbook,sheet,table,match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 50 }, maxChars: 20000, tableMaxRows: 8, tableMaxCols: 16 });
await fs.writeFile(`${outDir}/final_inspect.ndjson`, inspect.ndjson, "utf8");

for (const sheetName of ["요약_Summary", "툴빈도_Tools", "학습격차_LearningGaps"]) {
  const preview = await wb.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  await fs.writeFile(`${outDir}/qa_${sheetName}.png`, new Uint8Array(await preview.arrayBuffer()));
}

console.log(JSON.stringify({ outPath, sheets: wb.worksheets.items.map(s => s.name) }, null, 2));
