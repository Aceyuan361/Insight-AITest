import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useAgentProfileStore, DEFAULT_AGENT_NAME, compressImage } from '../store/agentProfileStore';
import { RADIUS, SPRING, text } from './agentStyles';
import { Pencil, Check, RotateCcw, X } from 'lucide-react';
import agentAvatarDefault from '../../../assets/agent-avatar.jpg';

/**
 * 侧边栏底部：Agent 身份卡（头像 + 名字 + 编辑入口）。
 *
 * 取代原「设置」按钮（设置入口收敛到全局 TopBar 齿轮）。
 * 点编辑 → 行内展开编辑区（改名 + 换头像 + 重置）。
 * 移动端：触控目标 ≥44px。
 */
export function AgentIdentityCard({ isMobile }: { isMobile?: boolean }) {
  const { name, avatar, setName, setAvatar, reset } = useAgentProfileStore();
  const [editing, setEditing] = useState(false);
  const [draftName, setDraftName] = useState(name);
  const [avatarError, setAvatarError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const { t } = useTranslation();

  const avatarSrc = avatar ?? agentAvatarDefault;
  const minTarget = isMobile ? { minWidth: 44, minHeight: 44 } : {};

  const startEdit = () => {
    setDraftName(name);
    setAvatarError(null);
    setEditing(true);
  };

  const cancelEdit = () => {
    setEditing(false);
    setAvatarError(null);
  };

  const save = () => {
    setName(draftName);
    setEditing(false);
  };

  const onPickAvatar = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (!file.type.startsWith('image/')) {
      setAvatarError(t('ai.chooseImage'));
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setAvatarError(t('ai.imageTooLarge'));
      return;
    }
    try {
      const compressed = await compressImage(file);
      setAvatar(compressed);
      setAvatarError(null);
    } catch {
      setAvatarError(t('ai.imageProcessFailed'));
    }
    if (fileRef.current) fileRef.current.value = '';
  };

  if (editing) {
    return (
      <div
        style={{
          padding: 12,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
          borderTop: '1px solid var(--bg-card)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          {/* 头像预览（点击换图） */}
          <button
            onClick={() => fileRef.current?.click()}
            title={t('ai.changeAvatar')}
            style={{
              width: 40, height: 40, borderRadius: '50%', padding: 0, cursor: 'pointer',
              border: '1px solid var(--border-strong)', overflow: 'hidden',
              flexShrink: 0, position: 'relative', background: 'none',
            }}
          >
            <img src={avatarSrc} alt={t('ai.avatarAlt')} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/png,image/jpeg,image/webp,image/gif"
            onChange={(e) => onPickAvatar(e.target.files)}
            hidden
          />
          <input
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') save();
              if (e.key === 'Escape') cancelEdit();
            }}
            maxLength={20}
            autoFocus
            placeholder={DEFAULT_AGENT_NAME}
            aria-label={t('ai.agentNameLabel')}
            style={{
              flex: 1, minWidth: 0, background: 'var(--bg-card)', border: '1px solid var(--border-strong)',
              borderRadius: RADIUS.sm, color: text.primary, padding: '6px 10px',
              fontFamily: 'inherit', fontSize: 13, outline: 'none',
            }}
          />
        </div>
        {avatarError && (
          <div style={{ fontSize: 11, color: text.danger }}>{avatarError}</div>
        )}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            onClick={save}
            title={t('ai.saveTitle')}
            style={{
              ...minTarget, background: text.accent, color: 'var(--bg-base)', border: 'none',
              borderRadius: RADIUS.sm, padding: '5px 10px', cursor: 'pointer', fontSize: 12,
              fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4,
            }}
          >
            <Check size={13} strokeWidth={2} />{t('ai.saveName')}
          </button>
          <button
            onClick={() => { reset(); setDraftName(DEFAULT_AGENT_NAME); setAvatarError(null); }}
            title={t('ai.resetDefaultTitle')}
            style={{
              ...minTarget, background: 'none', border: '1px solid var(--bg-elevated)',
              color: text.muted, borderRadius: RADIUS.sm, padding: '5px 10px', cursor: 'pointer',
              fontSize: 11, display: 'inline-flex', alignItems: 'center', gap: 4,
            }}
          >
            <RotateCcw size={12} strokeWidth={1.5} />{t('ai.resetDefault')}
          </button>
          <div style={{ flex: 1 }} />
          <button
            onClick={cancelEdit}
            title={t('ai.cancelTitle')}
            style={{
              ...minTarget, background: 'none', border: 'none', color: text.muted,
              cursor: 'pointer', padding: '5px', display: 'inline-flex', alignItems: 'center',
            }}
          >
            <X size={14} strokeWidth={1.5} />
          </button>
        </div>
      </div>
    );
  }

  // 默认态：头像 + 名字 + 编辑铅笔
  return (
    <div
      style={{
        padding: 12,
        borderTop: '1px solid var(--bg-card)',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
      }}
    >
      <img
        src={avatarSrc}
        alt={t('ai.avatarWithNameAlt', { name })}
        style={{
          width: 36, height: 36, borderRadius: '50%', objectFit: 'cover',
          border: '1px solid var(--border)', flexShrink: 0,
        }}
      />
      <span style={{ fontSize: 13, color: text.secondary, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {name}
      </span>
      <button
        onClick={startEdit}
        title={t('ai.editIdentity')}
        aria-label={t('ai.editIdentity')}
        style={{
          ...minTarget, background: 'none', border: 'none', color: text.muted, cursor: 'pointer',
          padding: 6, display: 'inline-flex', alignItems: 'center',
          transition: `color 0.2s ${SPRING}`,
        }}
        onMouseEnter={(e) => (e.currentTarget.style.color = text.accent)}
        onMouseLeave={(e) => (e.currentTarget.style.color = text.muted)}
      >
        <Pencil size={13} strokeWidth={1.5} />
      </button>
    </div>
  );
}
