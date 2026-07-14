export function MissingModule({ entry }: { entry: string }) {
  return (
    <div style={{ padding: 48, color: "var(--text-primary)" }}>
      <h2>模块前端未注册</h2>
      <p>
        清单中声明了 <code>{entry}</code>，但未在 module-map 中映射。
      </p>
      <p>
        请在 <code>src/module-map.ts</code> 添加该模块的映射。
      </p>
    </div>
  );
}
