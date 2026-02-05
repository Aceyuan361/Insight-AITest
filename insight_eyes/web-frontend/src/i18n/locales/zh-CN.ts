/**
 * 简体中文翻译
 */
export default {
  translation: {
    // === 通用 ===
    common: {
      loading: '加载中...',
      save: '保存',
      cancel: '取消',
      confirm: '确认',
      delete: '删除',
      refresh: '刷新',
      search: '搜索',
      export: '导出',
      import: '导入',
      close: '关闭',
      back: '返回',
      next: '下一步',
      previous: '上一步',
      submit: '提交',
      reset: '重置',
      apply: '应用',
      ok: '确定',
      yes: '是',
      no: '否',
      all: '全部',
      none: '无',
      total: '共',
      items: '项',
      language: '语言',
      chinese: '简体中文',
      english: 'English',
    },

    // === 菜单栏 ===
    menu: {
      projectName: 'Insight Eye',
      realtimeMonitor: '实时监控',
      testReport: '测试报告',
      help: '帮助',
      monitoring: '监控中',
      notMonitoring: '未监控',
    },

    // === 状态栏 ===
    statusBar: {
      noDevice: '未选择设备',
    },

    // === 设备选择面板 ===
    device: {
      title: '设备',
      app: '应用',
      currentTarget: '当前目标',
      startMonitor: '开始监控',
      stopMonitor: '停止监控',
      refreshDevices: '刷新设备',
      noDevices: '暂无设备',
      noApps: '暂无应用',
      deviceOnline: '在线',
      deviceOffline: '离线',
      deviceUnauthorized: '未授权',
      battery: '电池',
      batteryLevel: '电量',
      temperature: '温度',
      capacity: '容量',
      selectDeviceFirst: '请先选择设备',
      selectAppFirst: '请先选择应用',
      startMonitorHint: '选择设备并点击"开始监控"开始性能监控',
      appPackagePlaceholder: '应用包名 (如: com.example.app)',
      startMonitorFailed: '启动监控失败',
      stopMonitorFailed: '停止监控失败',
      starting: '启动中...',
      stopping: '停止中...',

      // 警告对话框
      appNotRunning: '应用未运行',
      appNotRunningMessage: '应用当前未在前台运行，是否继续开始监控？',
      appInBackground: '后台运行',
      appInBackgroundMessage: '应用当前在后台运行，可能无法获取完整的性能数据，是否继续？',

      // iOS GPU 限制
      iosNotSupported: 'iOS不支持',
      iosGpuWarningTitle: 'iOS GPU 监控限制',
      iosGpuWarningMessage: '抱歉，iOS 设备暂不支持 GPU 监控。',
      iosGpuWarningReason: '原因：',
      iosGpuWarningReason1: 'iOS 系统 DVT 通道无法获取 GPU 能耗数据',
      iosGpuWarningReason2: 'CLI 能耗命令超时（20+ 秒），不适合实时监控',
      iosGpuWarningAvailable: '已启用指标：',
      iosGpuWarningFeature1: 'CPU 使用率 ✓',
      iosGpuWarningFeature2: '内存使用 ✓',
      iosGpuWarningFeature3: 'FPS（系统刷新率参考）✓',
      iosGpuWarningFeature4: '网络流量（系统级）✓',
      iosGpuWarningFeature5: '电池状态 ✓',
      iosGpuWarningButton: '我知道了',
    },

    // === 配置面板 ===
    config: {
      title: '采集配置',
      samplingRate: '采样频率',
      monitoringMetrics: '监控指标',
      alertThresholds: '告警阈值',
      advanced: '高级设置',

      // 采样率选项
      samplingRateOptions: {
        veryFast: '极快 (200ms)',
        fast: '快 (500ms)',
        normal: '正常 (1000ms)',
        slow: '慢 (2000ms)',
      },

      // 监控指标
      metrics: {
        cpu: 'CPU 使用率',
        memory: '内存使用',
        fps: '帧率',
        networkUp: '网络上行',
        networkDown: '网络下行',
        gpu: 'GPU 使用率',
      },

      // 告警阈值
      alerts: {
        fpsBelow: 'FPS 低于',
        memoryAbove: '内存超过',
        cpuAbove: 'CPU 超过',
        temperatureAbove: '温度超过',
      },

      // iOS GPU 限制提示
      iosGpuWarning: 'iOS 设备 GPU 指标需要开发者模式支持',

      // 数值输入
      setValue: '设置值为',

      // 配置操作
      confirmReset: '确定要重置为默认配置吗？',
      resetSuccess: '配置已重置为默认值',
      storageLocation: '配置存储在浏览器 localStorage 中。\n\n如需完全清除配置，请清除浏览器缓存。',
    },

    // === 报告面板 ===
    report: {
      title: '测试报告',
      allDevices: '全部设备',
      searchPlaceholder: '搜索包名或应用名',
      exportHtml: '导出 HTML 报告',
      deleteSession: '删除会话',
      batchDelete: '批量删除',
      selectSessions: '选择会话',

      // 表格列
      table: {
        index: '序号',
        time: '时间',
        appName: '应用名称',
        device: '设备',
        duration: '时长',
        actions: '操作',
      },

      // 状态
      noSessions: '暂无会话记录',
      sessionDetail: '会话详情',

      // 操作相关
      exportFailed: '导出报告失败',
      deleteFailed: '删除会话失败',
      confirmDeleteMessage: '确定要删除会话 {{sessionId}} 吗？\n\n此操作不可撤销，将删除该会话的所有数据和告警记录。',
      exporting: '导出中...',
      deleting: '删除中...',
      selectSessionPrompt: '请选择一个会话查看详情',
      selectedCount: '已选 {{count}} 项',
    },

    // === 会话列表 ===
    sessionList: {
      title: '会话列表',
      duration: '时长',
      startTime: '开始时间',
      endTime: '结束时间',
      viewDetail: '查看详情',
      exportData: '导出数据',
      selectSessionsFirst: '请先选择要删除的会话',
      confirmBatchDelete: '确定要删除选中的 {{count}} 个会话吗？\n\n此操作不可撤销，将删除这些会话的所有数据和告警记录。',
      deleteSuccess: '成功删除 {{count}} 个会话',
      deletePartialSuccess: '批量删除完成\n成功: {{success}} 个\n失败: {{failed}} 个\n\n失败的会话ID: {{ids}}',
      deleteFailed: '批量删除会话失败',
      durationSeconds: '{{count}}秒',
      durationMinutesSeconds: '{{minutes}}分{{seconds}}秒',
      durationHoursMinutes: '{{hours}}小时{{minutes}}分{{seconds}}秒',
      deviceId: '设备({{id}})',
      device: '设备',
      app: '应用',
      time: '时间',
      selectSession: '请选择一个会话查看图表',
      loadingCharts: '加载图表数据中...',
      noData: '该会话暂无指标数据',
      noDisplayableData: '暂无可显示的图表数据',
    },

    // === 告警记录 ===
    alerts: {
      title: '告警记录',
      noAlerts: '暂无告警记录',
      severity: '严重程度',
      severityCritical: '严重',
      severityWarning: '警告',
      severityInfo: '信息',
      time: '时间',
      message: '告警信息',
    },

    // === 帮助对话框 ===
    help: {
      title: '帮助',
      tabs: {
        quickStart: '快速开始',
        metrics: '监控指标说明',
        alerts: '告警功能',
        reports: '测试报告',
        about: '关于',
      },

      // 快速开始
      quickStart: {
        step1: '1. 选择设备',
        step1Desc: '从左侧面板选择要监控的 Android 或 iOS 设备',
        step2: '2. 选择应用',
        step2Desc: '从应用列表中选择要监控的应用程序',
        step3: '3. 配置参数',
        step3Desc: '在右侧面板配置采样率和监控指标',
        step4: '4. 开始监控',
        step4Desc: '点击"开始监控"按钮，查看实时性能数据',
        step5: '5. 查看报告',
        step5Desc: '监控结束后，在报告页面查看详细数据',
      },

      // 监控指标说明
      metrics: {
        title: '监控指标说明',
        cpuTitle: 'CPU 使用率',
        cpuDesc: '显示应用程序的 CPU 使用百分比，包括总 CPU 和应用专用 CPU',

        memoryTitle: '内存使用',
        memoryDesc: '显示应用程序的内存使用情况，包括 PSS（比例集大小）',

        fpsTitle: '帧率',
        fpsDesc: '显示应用程序的帧率，用于评估界面流畅度',

        networkTitle: '网络流量',
        networkDesc: '显示网络上传和下载速度',

        gpuTitle: 'GPU 使用率',
        gpuDesc: '显示 GPU 渲染使用率',
        gpuNote: '注意：Android GPU 监控暂未实现，iOS 受系统限制不支持',
      },

      // 平台支持说明
      platformSupport: {
        title: '平台支持',
        android: {
          title: 'Android 平台',
          osVersion: '支持系统：Android 7.0 及以上版本',
          features: '支持指标：CPU、内存、FPS、网络（上行/下行）、电池',
          gpuStatus: 'GPU 状态：暂不支持（开发中）',
          notes: '注意事项：需要启用 USB 调试模式',
        },
        ios: {
          title: 'iOS 平台',
          osVersion: '支持系统：iOS 16.x 版本（不支持 iOS 17+）',
          features: '支持指标：CPU、内存、FPS、网络（系统级）、电池',
          gpuStatus: 'GPU 状态：不支持',
          gpuReason: '不支持原因：',
          gpuReason1: '• iOS 系统 DVT 通道无法获取 GPU 能耗数据',
          gpuReason2: '• CLI 能耗命令超时（20+ 秒），不适合实时监控',
          notes: '注意事项：需要信任电脑并启用开发者模式',
        },
      },

      // 告警功能
      alertsFeature: {
        title: '告警功能',
        description: '当性能指标超过设定阈值时，系统会自动记录告警信息',
        fpsAlert: 'FPS 告警：当帧率低于设定值时触发',
        memoryAlert: '内存告警：当内存使用超过设定值时触发',
        cpuAlert: 'CPU 告警：当 CPU 使用超过设定值时触发',
        tempAlert: '温度告警：当设备温度超过设定值时触发',
      },

      // 测试报告
      reports: {
        title: '测试报告',
        description: '监控结束后，可以在报告页面查看详细的性能数据和图表',
        features: {
          charts: '可视化图表：显示 CPU、内存、FPS 等性能曲线',
          statistics: '统计数据：最大值、最小值、平均值',
          export: '导出功能：支持导出 HTML 格式的详细报告',
          comparison: '会话对比：支持多个会话的数据对比',
        },
      },

      // 关于
      about: {
        version: '版本',
        versionValue: '1.0.0',
        author: '作者',
        authorValue: 'Aceyuan361',
        description: 'Insight Eye 是一款专业的移动设备性能监控工具',
        features: '监控能力',
        featuresList: '实时 CPU、内存、FPS、网络性能监控',
        architecture: '技术架构',
        archDesc: '基于 React + Vite + ECharts 构建',
        license: '许可证',
        licenseValue: 'MIT',
        projectName: 'Insight Eye',

        // 平台支持详情
        platformSupport: '平台支持',
        androidSection: 'Android 平台',
        androidVersion: '支持系统：Android 7.0+',
        androidFeatures: '监控指标：CPU、内存、FPS、网络（上行/下行）、电池',
        androidGpu: 'GPU：暂不支持（开发中）',
        iosSection: 'iOS 平台',
        iosVersion: '支持系统：iOS 16.3.1+',
        iosFeatures: '监控指标：CPU、内存、FPS、网络（系统级）、电池',
        iosGpu: 'GPU：不支持',
        iosGpuReason: '原因：iOS 系统 DVT 限制，无法获取 GPU 能耗数据',
      },
    },

    // === 统计面板 ===
    stats: {
      max: '最大值',
      min: '最小值',
      avg: '平均值',
      current: '当前值',
      title: '性能统计',
      selectSession: '请选择一个会话',
      loading: '加载统计中...',
      network: '网络',
      alerts: '告警',
      noAlerts: '无告警记录',
      time: '时间',
      value: '数值',
    },

    // === 对话框提示 ===
    dialogs: {
      confirmDelete: '确认删除',
      confirmDeleteMessage: '确定要删除选中的会话吗？此操作不可恢复。',
      confirmStop: '确认停止',
      confirmStopMessage: '确定要停止当前监控吗？',
      operationSuccess: '操作成功',
      operationFailed: '操作失败',
      invalidInput: '输入无效',
      networkError: '网络错误，请检查连接',
    },

    // === 状态信息 ===
    status: {
      connecting: '连接中...',
      connected: '已连接',
      disconnected: '已断开',
      error: '错误',
      success: '成功',
      warning: '警告',
      info: '信息',
    },
  },
};
