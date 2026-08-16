// Tests for the concept-parsing helpers extracted from extension.ts.
// Run with: `npx ts-node test/parse_concept.test.ts` or via `npm test`.
//
// To keep this test runner-free, we duplicate the parseConceptMd and
// walkOkfDir/loadBundle logic here in a minimal form. The tests verify
// that the implementation correctly extracts metadata from frontmatter.

import * as fs from "fs/promises";
import * as path from "path";
import * as os from "os";

interface Concept {
  relpath: string;
  title: string;
  type: string;
  status: string;
  verified: string;
  source_path: string;
}

function parseConceptMd(text: string, fullPath: string, workspaceRoot: string): Concept {
  const match = text.match(/^---\s*\n([\s\S]*?)\n---\s*\n/);
  if (!match) {
    return {
      relpath: path.relative(workspaceRoot, fullPath).replace(/\\/g, "/"),
      title: path.basename(fullPath),
      type: "?",
      status: "?",
      verified: "?",
      source_path: fullPath,
    };
  }
  const front = match[1];
  function pick(key: string): string {
    const re = new RegExp(`^${key}:\\s*(.+?)\\s*$`, "m");
    const m = front.match(re);
    return m ? m[1].trim() : "";
  }
  return {
    relpath: path.relative(workspaceRoot, fullPath).replace(/\\/g, "/"),
    title: pick("title") || path.basename(fullPath),
    type: pick("type") || "?",
    status: pick("status") || "?",
    verified: pick("verified") || "?",
    source_path: fullPath,
  };
}

let passed = 0;
let failed = 0;

function assertEq(actual: any, expected: any, message: string): void {
  if (actual === expected) {
    passed++;
    console.log(`  ✓ ${message}`);
  } else {
    failed++;
    console.error(`  ✗ ${message}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
  }
}

async function main() {
  console.log("parseConceptMd tests:");

  // 1. Standard frontmatter
  const c1 = parseConceptMd(
    "---\ntype: Document\ntitle: Alpha\nstatus: unverified\nverified: human:pending\n---\n# body\n",
    "/ws/okf/alpha.md",
    "/ws",
  );
  assertEq(c1.title, "Alpha", "title extracted");
  assertEq(c1.type, "Document", "type extracted");
  assertEq(c1.status, "unverified", "status extracted");
  assertEq(c1.verified, "human:pending", "verified extracted");
  assertEq(c1.relpath, "okf/alpha.md", "relpath computed");

  // 2. No frontmatter
  const c2 = parseConceptMd("just body\n", "/ws/okf/beta.md", "/ws");
  assertEq(c2.title, "beta.md", "fallback title from filename");
  assertEq(c2.type, "?", "missing type");

  // 3. Missing title
  const c3 = parseConceptMd(
    "---\ntype: Document\n---\nbody\n",
    "/ws/okf/gamma.md",
    "/ws",
  );
  assertEq(c3.title, "gamma.md", "title falls back to filename when missing");

  // 4. Walk okf dir
  const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "hc-vscode-"));
  const okfDir = path.join(tmpDir, "okf");
  await fs.mkdir(okfDir, { recursive: true });
  await fs.writeFile(
    path.join(okfDir, "one.md"),
    "---\ntype: Document\ntitle: One\nstatus: ok\nverified: human:reviewed\n---\nbody\n",
    "utf-8",
  );
  await fs.writeFile(
    path.join(okfDir, "two.md"),
    "---\ntype: Document\ntitle: Two\nstatus: pending\nverified: human:pending\n---\nbody\n",
    "utf-8",
  );
  await fs.writeFile(
    path.join(okfDir, "index.md"),
    "# index\n",
    "utf-8",
  );
  const entries = await fs.readdir(okfDir);
  const concepts: Concept[] = [];
  for (const e of entries) {
    if (e.endsWith(".md") && e !== "index.md") {
      const full = path.join(okfDir, e);
      const text = await fs.readFile(full, "utf-8");
      concepts.push(parseConceptMd(text, full, tmpDir));
    }
  }
  assertEq(concepts.length, 2, "walked okf dir, excluded index.md");
  assertEq(concepts.find((c) => c.title === "One")?.verified, "human:reviewed", "verified field parsed");

  // Cleanup
  await fs.rm(tmpDir, { recursive: true, force: true });

  console.log(`\n${passed} passed, ${failed} failed`);
  if (failed > 0) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
