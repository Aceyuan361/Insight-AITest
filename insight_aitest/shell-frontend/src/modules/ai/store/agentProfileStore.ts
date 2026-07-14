import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Agent 身份偏好（名字 + 头像）。
 *
 * 设计：纯前端 localStorage 持久化。
 *   - 这是 UI 偏好，不进后端 LLMConfig（后者是 LLM 连接配置，语义不符）。
 *   - 头像以 base64 data URL 存储，客户端上传时压缩到 ≤256×256（约 < 50KB），localStorage 自包含。
 *
 * 默认名字「拾壹」，默认头像为 null（渲染时回退到静态资源 agent-avatar.jpg）。
 */

export const DEFAULT_AGENT_NAME = '拾壹';
const STORAGE_KEY = 'insight-eye-agent-profile';

export interface AgentProfileState {
  name: string;
  /** base64 data URL；null 时回退到默认静态头像 agent-avatar.jpg */
  avatar: string | null;

  setName: (name: string) => void;
  setAvatar: (avatar: string | null) => void;
  reset: () => void;
}

export const useAgentProfileStore = create<AgentProfileState>()(
  persist(
    (set) => ({
      name: DEFAULT_AGENT_NAME,
      avatar: null,

      setName: (name) => set({ name: name.trim() || DEFAULT_AGENT_NAME }),
      setAvatar: (avatar) => set({ avatar }),
      reset: () => set({ name: DEFAULT_AGENT_NAME, avatar: null }),
    }),
    {
      name: STORAGE_KEY,
      // 只持久化数据字段，不持久化 actions
      partialize: (s) => ({ name: s.name, avatar: s.avatar }),
    },
  ),
);

/**
 * 压缩图片到 ≤256×256 的 base64 data URL。
 * 用于头像上传：localStorage 体积控制（约 < 50KB）。
 * 失败时返回原图的 data URL（降级，不阻塞用户）。
 */
export async function compressImage(file: File, maxSize = 256, quality = 0.85): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        // 等比缩放到 maxSize 以内
        const scale = Math.min(1, maxSize / Math.max(img.width, img.height));
        const w = Math.round(img.width * scale);
        const h = Math.round(img.height * scale);
        const canvas = document.createElement('canvas');
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (!ctx) {
          // canvas 不可用，降级返回原图
          resolve(reader.result as string);
          return;
        }
        ctx.drawImage(img, 0, 0, w, h);
        // PNG 透明背景的头像用 image/png（JPEG 会变黑底）
        const isPng = file.type === 'image/png';
        resolve(canvas.toDataURL(isPng ? 'image/png' : 'image/jpeg', quality));
      };
      img.onerror = () => reject(new Error('图片解析失败'));
      img.src = reader.result as string;
    };
    reader.onerror = () => reject(new Error('图片读取失败'));
    reader.readAsDataURL(file);
  });
}
