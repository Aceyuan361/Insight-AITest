/**
 * 可拖动分割面板组件
 * 支持水平和垂直分割，保存位置到 localStorage
 */
import { useState, useRef, useEffect, useCallback } from 'react';

interface SplitPaneProps {
  direction?: 'horizontal' | 'vertical';
  defaultSize?: number; // 默认左侧/顶部尺寸（像素）
  minSize?: number; // 最小左侧/顶部尺寸
  maxSize?: number; // 最大左侧/顶部尺寸
  storageKey?: string; // localStorage 键名，用于保存位置
  children: [React.ReactNode, React.ReactNode]; // [左侧/顶部, 右侧/底部]
  className?: string;
}

export default function SplitPane({
  direction = 'horizontal',
  defaultSize = 300,
  minSize = 200,
  maxSize = 800,
  storageKey,
  children,
  className = '',
}: SplitPaneProps) {
  const [size, setSize] = useState(() => {
    // 从 localStorage 恢复保存的位置
    if (storageKey) {
      try {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
          const parsed = parseInt(saved, 10);
          if (!isNaN(parsed) && parsed >= minSize && parsed <= maxSize) {
            return parsed;
          }
        }
      } catch {
        // 忽略 localStorage 错误
      }
    }
    return defaultSize;
  });

  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const resizerRef = useRef<HTMLDivElement>(null);

  // 保存位置到 localStorage
  const saveSize = useCallback((newSize: number) => {
    setSize(newSize);
    if (storageKey) {
      try {
        localStorage.setItem(storageKey, newSize.toString());
      } catch {
        // 忽略 localStorage 错误
      }
    }
  }, [storageKey]);

  // 处理拖动
  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;

      const container = containerRef.current;
      const rect = container.getBoundingClientRect();

      let newSize: number;

      if (direction === 'horizontal') {
        // 水平分割：计算左边宽度
        newSize = e.clientX - rect.left;
      } else {
        // 垂直分割：计算顶部高度
        newSize = e.clientY - rect.top;
      }

      // 限制范围
      newSize = Math.max(minSize, Math.min(maxSize, newSize));
      saveSize(newSize);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging, direction, minSize, maxSize, saveSize]);

  // 处理拖动开始
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const isHorizontal = direction === 'horizontal';

  return (
    <div
      ref={containerRef}
      className={`flex ${isHorizontal ? 'flex-row' : 'flex-col'} ${className}`}
      style={{ position: 'relative', height: '100%', overflow: 'hidden' }}
    >
      {/* 左侧/顶部面板 */}
      <div
        style={{
          [isHorizontal ? 'width' : 'height']: `${size}px`,
          flexShrink: 0,
          overflow: 'hidden',
        }}
      >
        {children[0]}
      </div>

      {/* 拖动条 */}
      <div
        ref={resizerRef}
        onMouseDown={handleMouseDown}
        className={`flex-shrink-0 transition-colors ${
          isHorizontal ? 'w-1 cursor-col-resize' : 'h-1 cursor-row-resize'
        }`}
        style={{
          position: 'relative',
          zIndex: 10,
          backgroundColor: isDragging ? "var(--accent)" : 'var(--border-strong)',
        }}
        onMouseEnter={(e) => {
          if (!isDragging) {
            e.currentTarget.style.backgroundColor = 'rgba(0, 212, 255, 0.5)';
          }
        }}
        onMouseLeave={(e) => {
          if (!isDragging) {
            e.currentTarget.style.backgroundColor = 'var(--border-strong)';
          }
        }}
      >
        {/* 拖动指示器 */}
        <div
          className={`${
            isHorizontal
              ? 'absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2'
              : 'absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2'
          } ${isDragging ? 'opacity-100' : 'opacity-0'} group-hover:opacity-100 transition-opacity`}
        >
          {isHorizontal ? (
            <svg className="w-3 h-3 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="8" cy="12" r="1.5" />
              <circle cx="12" cy="12" r="1.5" />
              <circle cx="16" cy="12" r="1.5" />
            </svg>
          ) : (
            <svg className="w-3 h-3 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="8" r="1.5" />
              <circle cx="12" cy="12" r="1.5" />
              <circle cx="12" cy="16" r="1.5" />
            </svg>
          )}
        </div>
      </div>

      {/* 右侧/底部面板 */}
      <div
        style={{
          flex: 1,
          overflow: 'hidden',
          minWidth: 0,
          minHeight: 0,
        }}
      >
        {children[1]}
      </div>
    </div>
  );
}
