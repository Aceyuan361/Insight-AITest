import { type ReactNode } from 'react';
import * as Dialog from '@radix-ui/react-dialog';

/**
 * 模态弹窗。基于 Radix Dialog（focus trap / scroll lock / Esc / portal 自动）。
 * 外观沿用项目 inline 样式 + CSS vars（不引入 Tailwind class）。
 */
export function Modal({
  open,
  onOpenChange,
  children,
  title,
  width = 'min(420px, 90vw)',
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: ReactNode;
  title?: string;
  width?: string | number;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            zIndex: 2000,
            animation: 'modal-fade 200ms ease',
          }}
        />
        <Dialog.Content
          style={{
            position: 'fixed',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width,
            background: 'var(--bg-base)',
            border: '1px solid var(--bg-elevated)',
            borderRadius: 10,
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            overflow: 'hidden',
            zIndex: 2001,
            animation: 'modal-zoom 200ms cubic-bezier(0.16, 1, 0.3, 1)',
            outline: 'none',
          }}
        >
          {title && (
            <Dialog.Title style={{ padding: '20px 20px 8px', color: 'var(--text-primary)', fontSize: 14, fontWeight: 600 }}>
              {title}
            </Dialog.Title>
          )}
          {/* Radix 要求 Title 存在用于 a11y；无 title 时用 visually-hidden 兜底 */}
          {!title && (
            <Dialog.Title style={{ position: 'absolute', width: 1, height: 1, padding: 0, margin: -1, overflow: 'hidden', clip: 'rect(0 0 0 0)', whiteSpace: 'nowrap', border: 0 }}>
              dialog
            </Dialog.Title>
          )}
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
