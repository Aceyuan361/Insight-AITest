import { Toaster as Sonner, type ToasterProps } from "sonner";
import { useThemeStore } from "@/shared/store/themeStore";

/**
 * shadcn/ui 风格的 Toast 容器。
 * 取代全仓 17 处 alert()（spec §4.4）。
 * 挂载点：AppShell，与 ConfirmDialog 同层。
 */
const Toaster = ({ ...props }: ToasterProps) => {
  const theme = useThemeStore((s) => s.theme);
  return (
    <Sonner
      theme={theme}
      className="toaster group"
      style={
        {
          "--normal-bg": "var(--bg-card)",
          "--normal-text": "var(--text-primary)",
          "--normal-border": "var(--border-strong)",
          "--success-bg": "var(--bg-card)",
          "--success-text": "var(--success)",
          "--success-border": "var(--success)",
          "--error-bg": "var(--bg-card)",
          "--error-text": "var(--error)",
          "--error-border": "var(--error)",
          "--warning-bg": "var(--bg-card)",
          "--warning-text": "var(--warning)",
          "--warning-border": "var(--warning)",
        } as React.CSSProperties
      }
      toastOptions={{
        style: {
          background: "var(--bg-card)",
          color: "var(--text-primary)",
          border: "1px solid var(--border-strong)",
          borderRadius: "var(--radius-md, 8px)",
          boxShadow: "var(--shadow-card)",
        },
      }}
      {...props}
    />
  );
};

export { Toaster };
