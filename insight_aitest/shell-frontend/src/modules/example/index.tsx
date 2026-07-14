import { Sparkles } from 'lucide-react';

export function ExampleApp() {
  return (
    <div style={{ padding: 48, color: "var(--text-primary)" }}>
      <h1>示例模块</h1>
      <p>这是一个占位模块，用于验证平台模块机制。</p>
      <p style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
        如果你在 Dashboard 和侧边栏看到了它，说明模块化机制成立。<Sparkles size={14} strokeWidth={1.5} />
      </p>
    </div>
  );
}

export default ExampleApp;
