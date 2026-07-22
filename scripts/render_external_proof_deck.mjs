#!/usr/bin/env node
/** Render an evidence-linked external-proof manifest as an editable PPTX.
 *
 * The renderer deliberately accepts only the compiler's draft manifest and
 * never grants publication authority.  @oai/artifact-tool is resolved from an
 * initialized external workspace supplied with --workspace.
 */

import fs from "node:fs/promises";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";

function args(argv) {
  const result = {};
  for (let index = 2; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || !value) throw new Error("arguments must be --key value pairs");
    result[key.slice(2)] = value;
  }
  for (const required of ["manifest", "output", "workspace"]) {
    if (!result[required]) throw new Error(`missing --${required}`);
  }
  return result;
}

function requireDraftManifest(document) {
  if (document.schema_version !== "1.0" || document.mode !== "draft" || document.authority_level !== "A1") {
    throw new Error("deck renderer accepts only schema 1.0 A1 draft manifests");
  }
  if (!Array.isArray(document.claims) || !Array.isArray(document.slides) || document.claims.length === 0) {
    throw new Error("manifest needs claims and slides");
  }
  const claims = new Map();
  for (const claim of document.claims) {
    if (!/^([CL])\d+$/.test(claim.id) || !["fact", "limitation"].includes(claim.kind)) {
      throw new Error(`invalid claim ${claim.id}`);
    }
    if (!claim.statement?.trim() || !Array.isArray(claim.evidence) || claim.evidence.length === 0) {
      throw new Error(`claim ${claim.id} is not evidence-backed`);
    }
    claims.set(claim.id, claim);
  }
  for (const slide of document.slides) {
    if (!slide.title?.trim() || !Array.isArray(slide.claim_ids) || slide.claim_ids.length === 0) {
      throw new Error("every slide needs a title and claim IDs");
    }
    for (const id of slide.claim_ids) if (!claims.has(id)) throw new Error(`unknown slide claim ${id}`);
  }
  return claims;
}

function addText(slide, text, position, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox", position, fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: "Helvetica Neue", color: "#111111", fontSize: 20,
    autoFit: "shrinkText", ...style,
  };
  return shape;
}

function addChrome(slide, number, claimIds) {
  addText(slide, "EVIDENCE-BACKED VIRTUAL TWIN", { left: 42, top: 34, width: 420, height: 28 },
    { fontSize: 14, bold: true, color: "#666666" });
  addText(slide, claimIds.join(" · "), { left: 42, top: 662, width: 500, height: 22 },
    { fontSize: 12, color: "#666666" });
  addText(slide, String(number), { left: 1184, top: 660, width: 54, height: 22 },
    { fontSize: 12, color: "#666666", alignment: "right" });
}

function evidenceNote(claim) {
  const lines = [`${claim.id} · ${claim.kind.toUpperCase()}`, claim.statement, "", "Evidence:"];
  for (const source of claim.evidence) {
    lines.push(`- ${source.path}: ${source.needles.join(" | ")}`);
  }
  lines.push("", "Draft A1 evidence pack. Human review is required before external use.");
  return lines.join("\n");
}

async function writeBlob(filename, blob) {
  await fs.writeFile(filename, new Uint8Array(await blob.arrayBuffer()));
}

async function main() {
  const options = args(process.argv);
  const manifestPath = path.resolve(options.manifest);
  const outputPath = path.resolve(options.output);
  const workspace = path.resolve(options.workspace);
  const document = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  const claims = requireDraftManifest(document);

  const localRequire = createRequire(path.join(workspace, "package.json"));
  const modulePath = localRequire.resolve("@oai/artifact-tool");
  const { Presentation, PresentationFile } = await import(pathToFileURL(modulePath));
  const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

  const title = presentation.slides.add();
  title.background.fill = "#F7F7F5";
  addText(title, "DRAFT · A1", { left: 42, top: 40, width: 300, height: 32 },
    { fontSize: 16, bold: true, color: "#666666" });
  addText(title, document.title, { left: 42, top: 176, width: 1000, height: 240 },
    { fontSize: 58, bold: true, autoFit: "shrinkText" });
  addText(title, document.summary, { left: 42, top: 474, width: 840, height: 100 },
    { fontSize: 25, color: "#444444" });
  addText(title, "Evidence-linked technical case study · not approved for publication",
    { left: 42, top: 642, width: 850, height: 28 }, { fontSize: 14, color: "#666666" });
  title.speakerNotes.textFrame.setText("Open with the trust problem: model output is not authority. This deck contains only manifest-bound claims.");

  document.slides.forEach((spec, index) => {
    const claim = claims.get(spec.claim_ids[0]);
    const slide = presentation.slides.add();
    slide.background.fill = index === document.slides.length - 1 ? "#F3F0EA" : "#FFFFFF";
    addChrome(slide, index + 2, spec.claim_ids);
    addText(slide, spec.title, { left: 42, top: 88, width: 1120, height: 88 },
      { fontSize: 38, bold: true });
    addText(slide, claim.id, { left: 42, top: 235, width: 190, height: 150 },
      { fontSize: 74, bold: true, color: claim.kind === "limitation" ? "#9A4B2F" : "#236B57" });
    addText(slide, claim.statement, { left: 290, top: 226, width: 875, height: 210 },
      { fontSize: 30, bold: true, autoFit: "shrinkText" });
    const sourceCount = claim.evidence.length;
    const needleCount = claim.evidence.reduce((total, source) => total + source.needles.length, 0);
    addText(slide, `${sourceCount} source${sourceCount === 1 ? "" : "s"}`, { left: 290, top: 486, width: 260, height: 55 },
      { fontSize: 25, bold: true });
    addText(slide, `${needleCount} exact evidence match${needleCount === 1 ? "" : "es"}`, { left: 650, top: 486, width: 420, height: 55 },
      { fontSize: 25, bold: true });
    addText(slide, claim.kind === "limitation" ? "Explicitly unproven" : "Deterministically traced",
      { left: 290, top: 561, width: 620, height: 46 },
      { fontSize: 20, color: "#555555" });
    slide.speakerNotes.textFrame.setText(evidenceNote(claim));
  });

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const qaDirectory = path.join(workspace, "qa");
  await fs.mkdir(qaDirectory, { recursive: true });
  for (const [index, slide] of presentation.slides.items.entries()) {
    const stem = `slide-${String(index + 1).padStart(2, "0")}`;
    await writeBlob(path.join(qaDirectory, `${stem}.png`), await presentation.export({ slide, format: "png", scale: 1 }));
    const layout = await slide.export({ format: "layout" });
    await fs.writeFile(path.join(qaDirectory, `${stem}.layout.json`), await layout.text());
  }
  await writeBlob(path.join(qaDirectory, "montage.webp"),
    await presentation.export({ format: "webp", montage: true, scale: 1 }));
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);
  const receipt = {
    schema_version: "1.0", status: "rendered-draft", authority_level: "A1",
    manifest: path.relative(process.cwd(), manifestPath), output: path.relative(process.cwd(), outputPath),
    slides: presentation.slides.items.length, claims: claims.size,
  };
  await fs.writeFile(`${outputPath}.receipt.json`, `${JSON.stringify(receipt, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify(receipt)}\n`);
}

main().catch((error) => { console.error(error.stack || error); process.exitCode = 1; });
