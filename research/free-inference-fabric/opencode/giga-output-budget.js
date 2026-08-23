import { writeFileSync } from "node:fs";

let invocationCount = 0;

export const GigaOutputBudget = async () => {
  const expectedProvider = process.env.GIGA_OPENCODE_EXPECTED_PROVIDER;
  const expectedModel = process.env.GIGA_OPENCODE_EXPECTED_MODEL;
  const maxOutputTokens = Number.parseInt(process.env.GIGA_OPENCODE_MAX_OUTPUT_TOKENS ?? "", 10);
  const initReceipt = process.env.GIGA_OPENCODE_INIT_RECEIPT;
  const hookReceipt = process.env.GIGA_OPENCODE_HOOK_RECEIPT;
  if (
    expectedProvider !== "openrouter" ||
    !expectedModel ||
    !Number.isSafeInteger(maxOutputTokens) ||
    maxOutputTokens <= 0 ||
    !initReceipt ||
    !hookReceipt
  ) {
    throw new Error("invalid GIGA OpenCode admission environment");
  }
  writeFileSync(initReceipt, "loaded", { mode: 0o600 });

  return {
    "chat.params": async (input, output) => {
      invocationCount += 1;
      if (invocationCount !== 1) throw new Error("multiple LLM invocations denied");
      if (input.model.providerID !== expectedProvider || input.model.id !== expectedModel) {
        throw new Error("unadmitted model invocation denied");
      }
      output.maxOutputTokens = maxOutputTokens;
      writeFileSync(
        hookReceipt,
        JSON.stringify({
          invocationCount,
          providerID: input.model.providerID,
          modelID: input.model.id,
          maxOutputTokens: output.maxOutputTokens,
        }),
        { mode: 0o600 },
      );
    },
  };
};
