import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * 合并 Tailwind 类名：clsx 处理条件类，twMerge 去重冲突。
 * shadcn/ui 约定的统一类名拼接入口。
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
