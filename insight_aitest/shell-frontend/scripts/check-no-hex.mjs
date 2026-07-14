// @ts-nocheck
/**
 * 禁硬编码色 lint —— Stage 2 护栏。
 *
 * 扫描 src/ 下 .tsx/.ts，禁止裸 #rrggbb 颜色（应用代码必须用 var(--*) 语义 token）。
 *
 * 例外（允许含 hex）：
 *   - tokens.css / chart-tokens.ts（token 定义本身）
 *   - index.css（@theme 映射）
 *   - components/ui/sonner.tsx（shadcn 包装，手写 var）
 *   - htmlExporter.ts / runReportHtml.ts（报告导出，独立 HTML，不属于 app 主题）
 *   - .svg 资源
 *   - check-no-hex.mjs（脚本自身）
 *
 * 用法：node scripts/check-no-hex.mjs   退出码 0=通过，1=发现违规
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, extname } from "node:path";

const ROOT = "src";
const ALLOW = [
  "src/shared/theme/tokens.css",
  "src/shared/theme/chart-tokens.ts",
  "src/index.css",
  "src/components/ui/sonner.tsx",
  "src/shared/api/htmlExporter.ts",
  "src/modules/api/report/runReportHtml.ts",
];

function walk(dir) {
  const out = [];
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    const st = statSync(p);
    if (st.isDirectory()) out.push(...walk(p));
    else {
      const ext = extname(p);
      if (ext === ".ts" || ext === ".tsx" || ext === ".css") out.push(p);
    }
  }
  return out;
}

const files = walk(ROOT).map((f) => f.replace(/\\/g, "/"));
const violations = [];
// 匹配裸颜色 hex：# 后 3/6/8 位 hex，前面不是字母/数字/(/（避免 #cite-1 锚点、regex 等）
const HEX_RE = /(?<![0-9a-zA-Z/(])#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b/g;

for (const file of files) {
  if (ALLOW.includes(file)) continue;
  const content = readFileSync(file, "utf8");
  const lines = content.split("\n");
  lines.forEach((line, i) => {
    // 跳过注释行和 import type 行
    const trimmed = line.trim();
    if (trimmed.startsWith("//") || trimmed.startsWith("*") || trimmed.startsWith("/*"))
      return;
    const matches = line.match(HEX_RE);
    if (matches) {
      violations.push({ file: file.replace(/^src\//, ""), line: i + 1, hex: matches, snippet: trimmed.slice(0, 80) });
    }
  });
}

if (violations.length === 0) {
  console.log("✓ no hardcoded color hex in app code (excludes token/report/svg files)");
  process.exit(0);
} else {
  console.log(`✗ found ${violations.length} hardcoded color hex violation(s):\n`);
  for (const v of violations) {
    console.log(`  ${v.file}:${v.line}  ${v.hex.join(", ")}`);
    console.log(`    ${v.snippet}\n`);
  }
  console.log("Use var(--*) from tokens.css instead. See docs/superpowers/specs/2026-07-05-stage2-design-system.md");
  process.exit(1);
}
