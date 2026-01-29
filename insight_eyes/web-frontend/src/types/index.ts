export interface Device {
  device_id: string;
  device_name: string;
  platform: 'android' | 'ios';
  status: 'online' | 'offline';
}

export interface Session {
  id: number;
  device_id: string;
  app_package: string;
  platform: string;
  status: 'created' | 'running' | 'stopped' | 'error';
  start_time: string;
  end_time?: string;
  duration?: number;
}

export interface MetricsData {
  timestamp: string;
  cpu?: number;
  memory?: number;
  fps?: number;
  network_up?: number;
  network_down?: number;
  battery?: number;
  temperature?: number;
}

export interface MetricCardConfig {
  metricId: keyof MetricsData;
  title: string;
  color: string;
  yMin?: number;
  yMax?: number;
  decimals: number;
  unit: string;
  enabled: boolean;
  priority: number;
}
