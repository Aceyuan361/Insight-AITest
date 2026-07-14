import {
  // 模块 / 平台导航
  Gauge, Bot, TestTube, Network, Settings, Home, BarChart3,
  BookOpen, FolderKanban, MonitorSmartphone,
  // 状态（替换勾/叉/警示/暂停/等待 等 emoji，Stage 4 启用）
  Check, X, AlertTriangle, Clock, Pause, Play, Loader,
  CircleCheck, CircleX, Info,
  // 业务操作（替换搜索/相机/闪点/保存 等 emoji，Stage 4 启用）
  Search, Camera, Sparkles, Save, Image,
  Trash2, Upload, Send,
  // 通用
  ChevronRight, ChevronDown, Plus, FileText, Lightbulb,
  TrendingUp, Activity, Cpu, Wifi, WifiOff,
  type LucideIcon,
} from 'lucide-react';

// 受控图标映射。新模块用新图标时在此加一行。
export const moduleIcons: Record<string, LucideIcon> = {
  Gauge,
  Bot,
  TestTube,
  Network,
  BookOpen,
  FolderKanban,
  MonitorSmartphone,
};

export const platformIcons = { Settings, Home, Overview: BarChart3, FolderKanban };

// 状态图标（Stage 4 替换 emoji 时统一从此引入）
export const statusIcons = {
  success: CircleCheck,
  error: CircleX,
  warning: AlertTriangle,
  info: Info,
  pending: Clock,
  running: Loader,
  paused: Pause,
  play: Play,
  done: Check,
  failed: X,
};

// 业务操作图标（Stage 4 替换 emoji 时统一从此引入）
export const actionIcons = {
  search: Search,
  camera: Camera,
  sparkles: Sparkles,
  save: Save,
  image: Image,
  trash: Trash2,
  upload: Upload,
  send: Send,
  add: Plus,
};

// 通用图标
export const commonIcons = {
  chevronRight: ChevronRight,
  chevronDown: ChevronDown,
  file: FileText,
  lightbulb: Lightbulb,
  trendingUp: TrendingUp,
  activity: Activity,
  cpu: Cpu,
  wifi: Wifi,
  wifiOff: WifiOff,
};

export function getIcon(name: string): LucideIcon | undefined {
  return moduleIcons[name];
}
