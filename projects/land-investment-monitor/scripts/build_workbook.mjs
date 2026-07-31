import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const [reportPath, outputPath, previewDir] = process.argv.slice(2);
if (!reportPath || !outputPath || !previewDir) {
  throw new Error(
    "Usage: node scripts/build_workbook.mjs <report.json> <output.xlsx> <preview-dir>",
  );
}

const report = JSON.parse(await fs.readFile(reportPath, "utf8"));
const workbook = Workbook.create();
workbook.comments.setSelf({ displayName: "User" });

const headers = [
  "№",
  "Статус",
  "Источник",
  "Адрес",
  "Ссылка",
  "Площадь, сот.",
  "Цена, ₽",
  "Цена/сотка, ₽",
  "Медиана 1 км, ₽/сот.",
  "Средняя кластера, ₽/сот.",
  "Дисконт к медиане",
  "Дисконт к кластеру",
  "Потенциальная маржа, ₽",
  "Кадастровая стоимость, ₽",
  "Дисконт к кадастру",
  "До воды, км",
  "Тип воды",
  "До станции, км",
  "Маршрут, км",
  "Доезд, мин",
  "Маршрут",
  "Деревья",
  "Сигналы торга",
  "Фото",
  "Дней на рынке",
  "Инвест-балл",
  "Балл «для души»",
  "Плюсы и минусы",
  "Риски / причины отсева",
  "До точки роста, км",
  "До риск-зоны, км",
  "Сравнимых лотов",
  "Коммуникации",
  "Подъезд",
  "Охрана / КПП",
  "До инфраструктуры, км",
  "Широта",
  "Долгота",
  "Кадастровый номер",
  "Взносы в год, ₽",
];

const lastColumn = "AN";
const titleFill = "#173B57";
const headerFill = "#245B78";
const paleBlue = "#EAF2F8";
const paleGreen = "#E8F5E9";
const paleRed = "#FDECEC";
const darkText = "#17202A";
const mutedText = "#566573";

function safeNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function yesNoUnknown(value, yesLabel, noLabel) {
  if (value === true) return yesLabel;
  if (value === false) return noLabel;
  return "нет данных";
}

function valueRows(items) {
  return items.map((item, index) => [
    index + 1,
    item.status,
    item.source,
    item.address,
    item.url,
    safeNumber(item.area_sotki),
    safeNumber(item.price_rub),
    null,
    safeNumber(item.neighborhood_median_pps),
    safeNumber(item.cluster_average_pps),
    null,
    null,
    null,
    safeNumber(item.cadastral_value_rub),
    null,
    safeNumber(item.distance_to_water_km),
    item.water_type || "",
    safeNumber(item.distance_to_station_km),
    safeNumber(item.route_distance_km),
    safeNumber(item.route_minutes),
    item.route_is_estimate ? "оценка" : "маршрутизатор",
    (item.trees || []).join(", "),
    (item.urgency_markers || []).join(", "),
    safeNumber(item.photo_count),
    safeNumber(item.listing_days),
    safeNumber(item.investment_score),
    safeNumber(item.soul_score),
    item.pros_cons || "",
    [...(item.risk_markers || []), ...(item.hard_filter_reasons || [])].join(", "),
    safeNumber(item.distance_to_future_growth_km),
    safeNumber(item.distance_to_adverse_zone_km),
    safeNumber(item.comparable_count),
    (item.utilities || []).join(", "),
    yesNoUnknown(item.asphalt_access, "асфальт", "не асфальт"),
    yesNoUnknown(item.security, "есть", "нет"),
    safeNumber(item.distance_to_infrastructure_km),
    safeNumber(item.lat),
    safeNumber(item.lon),
    item.cadastral_number || "",
    safeNumber(item.annual_fees_rub),
  ]);
}

for (const [sheetName, items] of Object.entries(report.sheets)) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(5);
  sheet.freezePanes.freezeColumns(2);

  sheet.getRange(`A1:${lastColumn}1`).merge();
  sheet.getRange("A1").values = [[`Монитор земельных участков — ${sheetName}`]];
  sheet.getRange(`A1:${lastColumn}1`).format = {
    fill: titleFill,
    font: { bold: true, color: "#FFFFFF", size: 16 },
    verticalAlignment: "center",
  };
  sheet.getRange(`A1:${lastColumn}1`).format.rowHeight = 30;

  sheet.getRange(`A2:${lastColumn}2`).merge();
  const warning = report.metadata.demo
    ? "ДЕМО-ДАННЫЕ: расчёты проверяют механику; адреса, ссылки, точки инфраструктуры и кадастровые значения не являются реальными предложениями."
    : "Рабочий отчёт: перед сделкой перепроверьте документы, ограничения, границы, коммуникации и кадастровые сведения по первичным источникам.";
  sheet.getRange("A2").values = [[warning]];
  sheet.getRange(`A2:${lastColumn}2`).format = {
    fill: report.metadata.demo ? "#FFF3CD" : paleBlue,
    font: { bold: true, color: report.metadata.demo ? "#7A5200" : darkText },
    wrapText: true,
  };
  sheet.getRange(`A2:${lastColumn}2`).format.rowHeight = 34;

  sheet.getRange(`A3:${lastColumn}3`).merge();
  sheet.getRange("A3").values = [[
    `Сформировано: ${report.metadata.generated_at} · объектов: ${items.length} · ` +
      `жёсткие фильтры: ≥${report.goal.min_area_sotki} сот., ${report.goal.allowed_land_categories.join("/")}, ` +
      `бюджет до ${(report.goal.max_budget_rub / 1_000_000).toFixed(1)} млн ₽ · ` +
      `красный порог: ${(report.goal.underpricing_red_threshold * 100).toFixed(0)}%`,
  ]];
  sheet.getRange(`A3:${lastColumn}3`).format = {
    fill: "#F4F6F7",
    font: { color: mutedText, italic: true },
    wrapText: true,
  };
  sheet.getRange(`A3:${lastColumn}3`).format.rowHeight = 28;

  sheet.getRange(`A5:${lastColumn}5`).values = [headers];
  sheet.getRange(`A5:${lastColumn}5`).format = {
    fill: headerFill,
    font: { bold: true, color: "#FFFFFF" },
    wrapText: true,
    verticalAlignment: "center",
    horizontalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: "#173B57" },
  };
  sheet.getRange(`A5:${lastColumn}5`).format.rowHeight = 46;

  const rows = valueRows(items);
  if (rows.length > 0) {
    const firstRow = 6;
    const lastRow = firstRow + rows.length - 1;
    sheet.getRange(`A${firstRow}:${lastColumn}${lastRow}`).values = rows;

    for (let row = firstRow; row <= lastRow; row += 1) {
      sheet.getRange(`H${row}`).formulas = [[`=IFERROR(G${row}/F${row},0)`]];
      sheet.getRange(`K${row}`).formulas = [[`=IFERROR((I${row}-H${row})/I${row},0)`]];
      sheet.getRange(`L${row}`).formulas = [[`=IFERROR((J${row}-H${row})/J${row},0)`]];
      sheet.getRange(`M${row}`).formulas = [[`=MAX(0,I${row}*F${row}-G${row})`]];
      sheet.getRange(`O${row}`).formulas = [[`=IF(N${row}>0,(N${row}-G${row})/N${row},0)`]];
    }

    sheet.getRange(`A${firstRow}:${lastColumn}${lastRow}`).format = {
      font: { color: darkText },
      verticalAlignment: "top",
      borders: {
        insideHorizontal: { style: "thin", color: "#DDE4E8" },
        bottom: { style: "thin", color: "#AAB7B8" },
      },
    };
    sheet.getRange(`D${firstRow}:E${lastRow}`).format.wrapText = true;
    sheet.getRange(`Q${firstRow}:W${lastRow}`).format.wrapText = true;
    sheet.getRange(`AB${firstRow}:AC${lastRow}`).format.wrapText = true;
    sheet.getRange(`AG${firstRow}:AI${lastRow}`).format.wrapText = true;
    sheet.getRange(`F${firstRow}:F${lastRow}`).format.numberFormat = "0.0";
    sheet.getRange(`G${firstRow}:J${lastRow}`).format.numberFormat = "#,##0";
    sheet.getRange(`K${firstRow}:L${lastRow}`).format.numberFormat = "0.0%";
    sheet.getRange(`M${firstRow}:N${lastRow}`).format.numberFormat = "#,##0";
    sheet.getRange(`O${firstRow}:O${lastRow}`).format.numberFormat = "0.0%";
    sheet.getRange(`P${firstRow}:T${lastRow}`).format.numberFormat = "0.0";
    sheet.getRange(`X${firstRow}:Y${lastRow}`).format.numberFormat = "0";
    sheet.getRange(`Z${firstRow}:AA${lastRow}`).format.numberFormat = "0.0";
    sheet.getRange(`AD${firstRow}:AE${lastRow}`).format.numberFormat = "0.0";
    sheet.getRange(`AF${firstRow}:AF${lastRow}`).format.numberFormat = "0";
    sheet.getRange(`AJ${firstRow}:AJ${lastRow}`).format.numberFormat = "0.0";
    sheet.getRange(`AK${firstRow}:AL${lastRow}`).format.numberFormat = "0.000000";
    sheet.getRange(`AN${firstRow}:AN${lastRow}`).format.numberFormat = "#,##0";

    sheet.getRange(`B${firstRow}:B${lastRow}`).conditionalFormats.add("containsText", {
      text: "КРАСНЫЙ",
      format: { fill: paleRed, font: { bold: true, color: "#B42318" } },
    });
    sheet.getRange(`K${firstRow}:K${lastRow}`).conditionalFormats.add("cellIs", {
      operator: "greaterThanOrEqual",
      formula: report.goal.underpricing_red_threshold,
      format: { fill: paleGreen, font: { bold: true, color: "#176B3A" } },
    });
    sheet.getRange(`L${firstRow}:L${lastRow}`).conditionalFormats.add("cellIs", {
      operator: "greaterThanOrEqual",
      formula: report.goal.cluster_anomaly_threshold,
      format: { fill: "#FFF3CD", font: { bold: true, color: "#8A5A00" } },
    });
    sheet.getRange(`Z${firstRow}:AA${lastRow}`).conditionalFormats.add("colorScale", {
      colors: ["#FDECEC", "#FFF3CD", "#DDF3E4"],
      thresholds: ["min", "50%", "max"],
    });
    sheet.getRange(`AF${firstRow}:AF${lastRow}`).conditionalFormats.add("cellIs", {
      operator: "lessThan",
      formula: 2,
      format: { fill: "#FFF3CD", font: { bold: true, color: "#8A5A00" } },
    });
    sheet.getRange(`X${firstRow}:X${lastRow}`).conditionalFormats.add("cellIs", {
      operator: "lessThan",
      formula: 3,
      format: { fill: "#FFF3CD", font: { bold: true, color: "#8A5A00" } },
    });
    sheet.tables.add(`A5:${lastColumn}${lastRow}`, true, `${sheetName.replace(/\s+/g, "")}Table`);
  } else {
    sheet.getRange(`A6:${lastColumn}7`).merge();
    sheet.getRange("A6").values = [[
      "Нет объектов, одновременно прошедших жёсткие фильтры и критерии этой вкладки.",
    ]];
    sheet.getRange(`A6:${lastColumn}7`).format = {
      fill: "#F8F9F9",
      font: { italic: true, color: mutedText },
      verticalAlignment: "center",
    };
  }

  const widths = {
    A: 5,
    B: 12,
    C: 10,
    D: 29,
    E: 25,
    F: 11,
    G: 15,
    H: 15,
    I: 17,
    J: 18,
    K: 15,
    L: 15,
    M: 19,
    N: 19,
    O: 15,
    P: 11,
    Q: 17,
    R: 13,
    S: 12,
    T: 12,
    U: 13,
    V: 19,
    W: 20,
    X: 8,
    Y: 13,
    Z: 12,
    AA: 13,
    AB: 48,
    AC: 26,
    AD: 16,
    AE: 15,
    AF: 15,
    AG: 22,
    AH: 14,
    AI: 14,
    AJ: 18,
    AK: 13,
    AL: 13,
    AM: 20,
    AN: 16,
  };
  for (const [column, width] of Object.entries(widths)) {
    sheet.getRange(`${column}1:${column}${Math.max(8, items.length + 5)}`).format.columnWidth = width;
  }

  workbook.comments.addThread(
    { cell: sheet.getRange("H5") },
    "Формула: цена объявления / площадь участка.",
  );
  workbook.comments.addThread(
    { cell: sheet.getRange("I5") },
    "Медиана цены за сотку среди сопоставимых лотов в радиусе 1 км; при нехватке данных используется кластер.",
  );
  workbook.comments.addThread(
    { cell: sheet.getRange("J5") },
    "Средняя цена за сотку среди других лотов того же кластера; текущий лот исключён.",
  );
  workbook.comments.addThread(
    { cell: sheet.getRange("M5") },
    "Иллюстративная валовая маржа до налогов, сделки, юристов, ремонта, финансирования и срока экспозиции.",
  );
  workbook.comments.addThread(
    { cell: sheet.getRange("AF5") },
    "Количество других лотов, использованных для локальной медианы. Значение меньше 2 требует особенно осторожной ручной проверки.",
  );
  workbook.comments.addThread(
    { cell: sheet.getRange("X5") },
    "Менее трёх фотографий считается сигналом слабой упаковки объявления; зимние и сумеречные фото требуют отдельного vision-анализатора.",
  );
}

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

for (const [sheetName, items] of Object.entries(report.sheets)) {
  const endRow = Math.max(8, Math.min(items.length + 5, 15));
  const preview = await workbook.render({
    sheetName,
    range: `A1:${lastColumn}${endRow}`,
    scale: 0.75,
    format: "png",
  });
  const safeName = sheetName.replace(/\s+/g, "-").toLowerCase();
  await fs.writeFile(
    path.join(previewDir, `${safeName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
await fs.writeFile(
  path.join(previewDir, "formula-errors.ndjson"),
  errors.ndjson || "",
  "utf8",
);

for (const sheetName of Object.keys(report.sheets)) {
  const inspected = await workbook.inspect({
    kind: "table",
    range: `'${sheetName}'!A1:AN15`,
    include: "values,formulas",
    tableMaxRows: 15,
    tableMaxCols: 40,
  });
  await fs.writeFile(
    path.join(previewDir, `${sheetName.replace(/\s+/g, "-").toLowerCase()}-inspect.ndjson`),
    inspected.ndjson || "",
    "utf8",
  );
  const formulaInspection = await workbook.inspect({
    kind: "formula",
    sheetId: sheetName,
    range: "H6:O15",
    options: { maxResults: 100 },
    maxChars: 8000,
  });
  await fs.writeFile(
    path.join(
      previewDir,
      `${sheetName.replace(/\s+/g, "-").toLowerCase()}-formulas.ndjson`,
    ),
    formulaInspection.ndjson || "",
    "utf8",
  );
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(outputPath);
