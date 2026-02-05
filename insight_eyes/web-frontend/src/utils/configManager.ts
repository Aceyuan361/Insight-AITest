/**
 * 配置管理工具
 *
 * 负责Web版配置的持久化存储，使用localStorage保存用户配置。
 *
 * 支持的配置项：
 * - samplingInterval: 采样间隔（字符串格式：'1s'/'3s'/'5s'/'10s'）
 * - enabledMetrics: 启用的监控指标列表
 * - alertThresholds: 告警阈值配置
 */

interface MonitoringConfig {
  samplingInterval: string;  // '1s' | '3s' | '5s' | '10s'
  enabledMetrics: string[];   // ['cpu', 'memory', 'fps', 'network_up', 'network_down', 'gpu']
  alertThresholds?: {         // 告警阈值
    fps: number;
    memory: number;
    cpu: number;
    temperature: number;
  };
}

const DEFAULT_CONFIG: MonitoringConfig = {
  samplingInterval: '1s',
  enabledMetrics: ['cpu', 'memory', 'fps', 'network_up', 'network_down'],
};

const CONFIG_KEY = 'insight_eye_monitoring_config';

/**
 * 配置管理器类
 */
class ConfigManager {
  /**
   * 加载配置
   *
   * 从localStorage加载配置，如果不存在则返回默认配置
   *
   * @returns 配置对象
   */
  loadConfig(): MonitoringConfig {
    try {
      const saved = localStorage.getItem(CONFIG_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        // 合并默认配置，确保新字段存在
        return {
          ...DEFAULT_CONFIG,
          ...parsed,
        };
      }
    } catch (error) {
      console.error('加载配置失败:', error);
    }
    return { ...DEFAULT_CONFIG };
  }

  /**
   * 保存配置
   *
   * 将配置保存到localStorage
   *
   * @param config 配置对象
   */
  saveConfig(config: MonitoringConfig): void {
    try {
      localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
    } catch (error) {
      console.error('保存配置失败:', error);
    }
  }

  /**
   * 更新采样间隔
   *
   * @param interval 采样间隔字符串 ('1s'/'3s'/'5s'/'10s')
   */
  saveSamplingInterval(interval: string): void {
    const config = this.loadConfig();
    config.samplingInterval = interval;
    this.saveConfig(config);
  }

  /**
   * 更新启用的指标
   *
   * @param metrics 启用的指标ID列表
   */
  saveEnabledMetrics(metrics: string[]): void {
    const config = this.loadConfig();
    config.enabledMetrics = metrics;
    this.saveConfig(config);
  }

  /**
   * 获取采样间隔
   *
   * @returns 采样间隔字符串
   */
  getSamplingInterval(): string {
    const config = this.loadConfig();
    return config.samplingInterval;
  }

  /**
   * 获取启用的指标
   *
   * @returns 启用的指标ID列表
   */
  getEnabledMetrics(): string[] {
    const config = this.loadConfig();
    return config.enabledMetrics;
  }

  /**
   * 清除配置
   *
   * 删除localStorage中的配置
   */
  clearConfig(): void {
    try {
      localStorage.removeItem(CONFIG_KEY);
    } catch (error) {
      console.error('清除配置失败:', error);
    }
  }

  /**
   * 保存告警阈值
   *
   * @param thresholds 告警阈值对象
   */
  saveAlertThresholds(thresholds: { fps: number; memory: number; cpu: number; temperature: number }): void {
    const config = this.loadConfig();
    config.alertThresholds = thresholds;
    this.saveConfig(config);
  }

  /**
   * 获取告警阈值
   *
   * @returns 告警阈值对象，如果不存在则返回默认值
   */
  getAlertThresholds(): { fps: number; memory: number; cpu: number; temperature: number } {
    const config = this.loadConfig();
    return config.alertThresholds || {
      fps: 30,
      memory: 500,
      cpu: 80,
      temperature: 45,
    };
  }

  /**
   * 重置为默认配置
   */
  resetToDefault(): void {
    this.saveConfig({ ...DEFAULT_CONFIG });
  }
}

// 导出单例实例
export const configManager = new ConfigManager();
