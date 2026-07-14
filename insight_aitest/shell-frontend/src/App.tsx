import { useEffect, useState } from 'react';
import { PlatformRouter } from './routing';
import type { ModuleManifest } from './shell/types';
import './index.css';

type State =
  | { status: 'loading' }
  | { status: 'ok'; modules: ModuleManifest[] }
  | { status: 'error'; message: string };

export default function App() {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    fetch('/api/platform/modules')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((modules: ModuleManifest[]) => setState({ status: 'ok', modules }))
      .catch((e) => setState({ status: 'error', message: String(e) }));
  }, []);

  if (state.status === 'loading') {
    return <div style={{ padding: 48, color: "var(--text-secondary)" }}>加载平台…</div>;
  }
  if (state.status === 'error') {
    return (
      <div style={{ padding: 48, color: "var(--text-primary)" }}>
        <h2>平台模块加载失败</h2>
        <p style={{ color: "var(--text-secondary)" }}>{state.message}</p>
        <button onClick={() => location.reload()}>重试</button>
      </div>
    );
  }
  return <PlatformRouter modules={state.modules} />;
}
