import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// The browser source must never contain Gnani credentials, auth headers, or the vendor endpoint.
// Vite's import.meta.env is used only for a public backend URL; it is not a secret.
const here = dirname(fileURLToPath(import.meta.url));
const FORBIDDEN = ["X-API-Key-ID", "api.vachana.ai", "vachana", "process.env"];
const KEY_LIKE = /\b[0-9a-f]{32}\b/i;

function sourceFiles(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) out.push(...sourceFiles(full));
    else if (!name.endsWith("security.test.js")) out.push(full);
  }
  return out;
}

test("frontend source contains no Gnani credential names or endpoints", () => {
  for (const file of sourceFiles(here)) {
    const text = readFileSync(file, "utf8");
    for (const term of FORBIDDEN) {
      assert.equal(text.includes(term), false, `${file} must not contain ${term}`);
    }
    assert.equal(KEY_LIKE.test(text), false, `${file} must not contain a key-shaped token`);
  }
});
