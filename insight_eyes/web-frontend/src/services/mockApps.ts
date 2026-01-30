/**
 * 模拟应用数据
 * 用于前端开发和演示
 */
import type { AppInfo } from '@/types';

export const mockApps: AppInfo[] = [
  {
    package_name: 'com.ss.android.ugc.aweme',
    app_name: '抖音',
    is_running: true,
  },
  {
    package_name: 'com.tencent.mm',
    app_name: '微信',
    is_running: true,
  },
  {
    package_name: 'com.tencent.mobileqq',
    app_name: 'QQ',
    is_running: false,
  },
  {
    package_name: 'com.taobao.taobao',
    app_name: '淘宝',
    is_running: false,
  },
  {
    package_name: 'com.alibaba.android.rimet',
    app_name: '钉钉',
    is_running: false,
  },
  {
    package_name: 'com.smile.gifmaker',
    app_name: '快手',
    is_running: true,
  },
  {
    package_name: 'com.bbk.appstore',
    app_name: 'vivo 应用商店',
    is_running: false,
  },
  {
    package_name: 'com.android.browser',
    app_name: '浏览器',
    is_running: false,
  },
];

/**
 * 获取设备的模拟应用列表
 */
export function getMockAppsForDevice(deviceId: string): AppInfo[] {
  // 可以根据设备ID返回不同的应用列表
  return mockApps;
}

/**
 * 根据包名获取应用名称
 */
export function getAppName(packageName: string): string {
  const app = mockApps.find(a => a.package_name === packageName);
  return app?.app_name || packageName;
}
