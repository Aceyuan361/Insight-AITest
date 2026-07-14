import { Link } from 'react-router-dom';

export function PlatformError() {
  return (
    <div style={{ padding: 48, color: "var(--text-primary)", textAlign: 'center' }}>
      <h2>平台发生错误</h2>
      <p>当前页面渲染失败。</p>
      <Link to="/" style={{ color: "var(--accent)" }}>
        返回首页
      </Link>
    </div>
  );
}
