export default function MenuBar() {
  return (
    <nav style={{
      backgroundColor: '#1e1e1e',
      borderBottom: '1px solid #333333',
      height: '36px',
    }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '100%',
        padding: '0 16px',
      }}>
        {/* 左侧：应用标题 */}
        <div style={{
          fontSize: '15px',
          fontWeight: '500',
          color: '#ffffff',
          fontFamily: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
        }}>
          性能监控工具
        </div>

        {/* 中间：菜单项 */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '20px',
        }}>
          <a
            href="#"
            onClick={(e) => e.preventDefault()}
            style={{
              fontSize: '13px',
              color: '#ffffff',
              textDecoration: 'none',
              fontFamily: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
            }}
          >
            文件(F)
          </a>
          <a
            href="#"
            onClick={(e) => e.preventDefault()}
            style={{
              fontSize: '13px',
              color: '#ffffff',
              textDecoration: 'none',
              fontFamily: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
            }}
          >
            编辑(E)
          </a>
          <a
            href="#"
            onClick={(e) => e.preventDefault()}
            style={{
              fontSize: '13px',
              color: '#ffffff',
              textDecoration: 'none',
              fontFamily: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
            }}
          >
            工具(T)
          </a>
          <a
            href="#"
            onClick={(e) => e.preventDefault()}
            style={{
              fontSize: '13px',
              color: '#ffffff',
              textDecoration: 'none',
              fontFamily: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
            }}
          >
            帮助(H)
          </a>
        </div>

        {/* 右侧：刷新设备按钮 */}
        <div>
          <button
            style={{
              backgroundColor: '#00bcd4',
              color: '#ffffff',
              border: 'none',
              borderRadius: '4px',
              padding: '4px 12px',
              fontSize: '12px',
              cursor: 'pointer',
              fontFamily: '"Microsoft YaHei UI", "Segoe UI", Arial, sans-serif',
            }}
          >
            刷新设备
          </button>
        </div>
      </div>
    </nav>
  );
}
