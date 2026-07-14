import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../store/conversationStore';
import { AttachmentChips } from './AttachmentChips';
import { CitationCard } from './CitationCard';
import { ThinkingPanel } from './ThinkingPanel';
import { Paperclip } from 'lucide-react';

/** 把回答正文里的 [n] 转成 Markdown 链接 [[n]](#cite-n)，供自定义 a 渲染器拦截。
 * 仅当本条消息有 citations 且 n 在范围内才转换（避免误伤普通 [数字] 文本）。 */
function citeTransform(content: string, citeCount: number): string {
  if (citeCount === 0) return content;
  // 先转义已有 Markdown 链接里的 [] 避免误改（简单起见：跳过 http 链接行的处理）
  return content.replace(/\[(\d+)\]/g, (m, n) => {
    const idx = parseInt(n, 10);
    return idx >= 1 && idx <= citeCount ? `[[${idx}]](#cite-${idx})` : m;
  });
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user';
  const [highlightedCite, setHighlightedCite] = useState<number | null>(null);
  const [flashKey, setFlashKey] = useState(0); // 重启闪烁动画用
  const { t } = useTranslation();

  const citeCount = message.citations?.length ?? 0;
  const rendered = isUser ? message.content : citeTransform(message.content, citeCount);

  const handleCitationClick = (n: number) => {
    setHighlightedCite(n);
    setFlashKey((k) => k + 1); // 重复点击同一引用时重新触发动画
    // 滚动到对应卡片
    requestAnimationFrame(() => {
      const el = document.querySelector(`[data-cite-index="${n}"]`);
      el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
  };

  return (
    <div style={{ marginBottom: 16 }}>
      <div
        style={{
          maxWidth: '80%',
          padding: 12,
          borderRadius: 8,
          background: isUser ? 'var(--bg-elevated)' : "var(--bg-card)",
          border: isUser ? '1px solid var(--bg-elevated)' : '1px solid var(--bg-card)',
          marginLeft: isUser ? 'auto' : 0,
        }}
      >
        <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>
          {isUser ? t('ai.you') : t('ai.aiAssistant')}
        </div>
        {!isUser && message.thinking && (
          <ThinkingPanel thinking={message.thinking} />
        )}
        <div className="markdown-body">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              a({ href, children, ...props }) {
                const m = href?.match(/^#cite-(\d+)$/);
                if (m) {
                  const n = parseInt(m[1], 10);
                  return (
                    <a
                      href={href}
                      className="cite-mark"
                      onClick={(e) => {
                        e.preventDefault();
                        handleCitationClick(n);
                      }}
                      {...props}
                    >
                      {children}
                    </a>
                  );
                }
                return (
                  <a href={href} target="_blank" rel="noreferrer" {...props}>
                    {children}
                  </a>
                );
              },
            }}
          >
            {rendered}
          </ReactMarkdown>
        </div>
      </div>
      {!isUser && message.citations && message.citations.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4, display: 'inline-flex', alignItems: 'center', gap: 4 }}><Paperclip size={12} strokeWidth={1.5} />{t('ai.referenceSource')}</div>
          {message.citations.map((c, i) => (
            <CitationCard
              key={`${i}-${flashKey}`}
              citation={c}
              index={i + 1}
              highlight={highlightedCite === i + 1}
            />
          ))}
        </div>
      )}
      {message.attachments && message.attachments.length > 0 && (
        <AttachmentChips attachments={message.attachments} />
      )}
    </div>
  );
}
