export default function MenuBar() {
  return (
    <nav className="bg-dark-card border-b border-gray-800">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center">
            <h1 className="text-xl font-bold text-neon-cpu">Insight-Eye</h1>
            <span className="ml-2 text-sm text-text-secondary">v1.0.3</span>
          </div>

          {/* 菜单项 */}
          <div className="flex items-center space-x-6">
            <a href="#" onClick={(e) => e.preventDefault()} className="text-text-secondary hover:text-white transition-colors">
              监控
            </a>
            <a href="#" onClick={(e) => e.preventDefault()} className="text-text-secondary hover:text-white transition-colors">
              报告
            </a>
            <a href="#" onClick={(e) => e.preventDefault()} className="text-text-secondary hover:text-white transition-colors">
              设置
            </a>
          </div>

          {/* 状态指示 */}
          <div className="flex items-center">
            <div className="flex items-center">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              <span className="ml-2 text-sm text-text-secondary">在线</span>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}
