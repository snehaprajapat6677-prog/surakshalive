import { test } from "node:test";
import assert from "node:assert/strict";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

// The browser bundle must never contain the Gnani key name, the API header, or the vendor endpoint.
const here = dirname(fileURLToPath(import.meta.url));
// The setting name GNANI_API_KEY may appear in user-facing text; the value and the vendor endpoint may not.
const FORBIDDEN = ["X-API-Key-ID", "api.vachana.ai", "vachana", "import.meta.env", "process.env"];
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
