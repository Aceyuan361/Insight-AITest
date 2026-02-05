/**
 * English Translation
 */
export default {
  translation: {
    // === Common ===
    common: {
      loading: 'Loading...',
      save: 'Save',
      cancel: 'Cancel',
      confirm: 'Confirm',
      delete: 'Delete',
      refresh: 'Refresh',
      search: 'Search',
      export: 'Export',
      import: 'Import',
      close: 'Close',
      back: 'Back',
      next: 'Next',
      previous: 'Previous',
      submit: 'Submit',
      reset: 'Reset',
      apply: 'Apply',
      ok: 'OK',
      yes: 'Yes',
      no: 'No',
      all: 'All',
      none: 'None',
      total: 'Total',
      items: 'items',
      language: 'Language',
      chinese: '简体中文',
      english: 'English',
    },

    // === Menu Bar ===
    menu: {
      projectName: 'Insight Eye',
      realtimeMonitor: 'Real-time Monitor',
      testReport: 'Test Report',
      help: 'Help',
      monitoring: 'Monitoring',
      notMonitoring: 'Not Monitoring',
    },

    // === Status Bar ===
    statusBar: {
      noDevice: 'No device selected',
    },

    // === Device Selection Panel ===
    device: {
      title: 'Device',
      app: 'Application',
      currentTarget: 'Current Target',
      startMonitor: 'Start Monitor',
      stopMonitor: 'Stop Monitor',
      refreshDevices: 'Refresh Devices',
      noDevices: 'No devices available',
      noApps: 'No apps available',
      deviceOnline: 'Online',
      deviceOffline: 'Offline',
      deviceUnauthorized: 'Unauthorized',
      battery: 'Battery',
      batteryLevel: 'Level',
      temperature: 'Temperature',
      capacity: 'Capacity',
      selectDeviceFirst: 'Please select a device first',
      selectAppFirst: 'Please select an application first',
      startMonitorHint: 'Select a device and click "Start Monitor" to begin performance monitoring',
      appPackagePlaceholder: 'App package (e.g. com.example.app)',
      startMonitorFailed: 'Failed to start monitoring',
      stopMonitorFailed: 'Failed to stop monitoring',
      starting: 'Starting...',
      stopping: 'Stopping...',

      // Warning dialogs
      appNotRunning: 'Application Not Running',
      appNotRunningMessage: 'The application is not currently running in the foreground. Do you want to start monitoring anyway?',
      appInBackground: 'Running in Background',
      appInBackgroundMessage: 'The application is currently running in the background. Complete performance data may not be available. Continue?',

      // iOS GPU restrictions
      iosNotSupported: 'iOS Not Supported',
      iosGpuWarningTitle: 'iOS GPU Monitoring Restrictions',
      iosGpuWarningMessage: 'Sorry, iOS devices do not currently support GPU monitoring.',
      iosGpuWarningReason: 'Reason:',
      iosGpuWarningReason1: 'iOS system DVT channel cannot access GPU energy data',
      iosGpuWarningReason2: 'CLI energy command times out (20+ seconds), not suitable for real-time monitoring',
      iosGpuWarningAvailable: 'Available metrics:',
      iosGpuWarningFeature1: 'CPU Usage ✓',
      iosGpuWarningFeature2: 'Memory Usage ✓',
      iosGpuWarningFeature3: 'FPS (System refresh rate reference) ✓',
      iosGpuWarningFeature4: 'Network Traffic (System-level) ✓',
      iosGpuWarningFeature5: 'Battery Status ✓',
      iosGpuWarningButton: 'Got it',
    },

    // === Configuration Panel ===
    config: {
      title: 'Collection Config',
      samplingRate: 'Sampling Rate',
      monitoringMetrics: 'Monitoring Metrics',
      alertThresholds: 'Alert Thresholds',
      advanced: 'Advanced Settings',

      // Sampling rate options
      samplingRateOptions: {
        veryFast: 'Very Fast (200ms)',
        fast: 'Fast (500ms)',
        normal: 'Normal (1000ms)',
        slow: 'Slow (2000ms)',
      },

      // Monitoring metrics
      metrics: {
        cpu: 'CPU Usage',
        memory: 'Memory Usage',
        fps: 'Frame Rate',
        networkUp: 'Network Upload',
        networkDown: 'Network Download',
        gpu: 'GPU Usage',
      },

      // Alert thresholds
      alerts: {
        fpsBelow: 'FPS Below',
        memoryAbove: 'Memory Above',
        cpuAbove: 'CPU Above',
        temperatureAbove: 'Temperature Above',
      },

      // iOS GPU restriction warning
      iosGpuWarning: 'iOS device GPU metrics require Developer Mode support',

      // Value input
      setValue: 'Set value to',

      // Config operations
      confirmReset: 'Are you sure you want to reset to default configuration?',
      resetSuccess: 'Configuration has been reset to default values',
      storageLocation: 'Configuration is stored in browser localStorage.\n\nTo completely clear configuration, please clear browser cache.',
    },

    // === Report Panel ===
    report: {
      title: 'Test Report',
      allDevices: 'All Devices',
      searchPlaceholder: 'Search package name or app name',
      exportHtml: 'Export HTML Report',
      deleteSession: 'Delete Session',
      batchDelete: 'Batch Delete',
      selectSessions: 'Select Sessions',

      // Table columns
      table: {
        index: '#',
        time: 'Time',
        appName: 'Application Name',
        device: 'Device',
        duration: 'Duration',
        actions: 'Actions',
      },

      // Status
      noSessions: 'No session records',
      sessionDetail: 'Session Detail',

      // Actions
      exportFailed: 'Failed to export report',
      deleteFailed: 'Failed to delete session',
      confirmDeleteMessage: 'Are you sure you want to delete session {{sessionId}}?\n\nThis action cannot be undone and will delete all data and alert records for this session.',
      exporting: 'Exporting...',
      deleting: 'Deleting...',
      selectSessionPrompt: 'Please select a session to view details',
      selectedCount: 'Selected {{count}} items',
    },

    // === Session List ===
    sessionList: {
      title: 'Session List',
      duration: 'Duration',
      startTime: 'Start Time',
      endTime: 'End Time',
      viewDetail: 'View Detail',
      exportData: 'Export Data',
      selectSessionsFirst: 'Please select sessions to delete first',
      confirmBatchDelete: 'Are you sure you want to delete {{count}} selected session(s)?\n\nThis action cannot be undone and will delete all data and alert records for these sessions.',
      deleteSuccess: 'Successfully deleted {{count}} session(s)',
      deletePartialSuccess: 'Batch delete completed\nSuccess: {{success}}\nFailed: {{failed}}\n\nFailed session IDs: {{ids}}',
      deleteFailed: 'Failed to batch delete sessions',
      durationSeconds: '{{count}}s',
      durationMinutesSeconds: '{{minutes}}m {{seconds}}s',
      durationHoursMinutes: '{{hours}}h {{minutes}}m {{seconds}}s',
      deviceId: 'Device({{id}})',
      device: 'Device',
      app: 'App',
      time: 'Time',
      selectSession: 'Please select a session to view charts',
      loadingCharts: 'Loading chart data...',
      noData: 'No metric data available for this session',
      noDisplayableData: 'No displayable chart data available',
    },

    // === Alert Records ===
    alerts: {
      title: 'Alert Records',
      noAlerts: 'No alert records',
      severity: 'Severity',
      severityCritical: 'Critical',
      severityWarning: 'Warning',
      severityInfo: 'Info',
      time: 'Time',
      message: 'Message',
    },

    // === Help Dialog ===
    help: {
      title: 'Help',
      tabs: {
        quickStart: 'Quick Start',
        metrics: 'Metrics Description',
        alerts: 'Alert Features',
        reports: 'Test Reports',
        about: 'About',
      },

      // Quick start
      quickStart: {
        step1: '1. Select Device',
        step1Desc: 'Select an Android or iOS device to monitor from the left panel',
        step2: '2. Select Application',
        step2Desc: 'Choose an application from the app list to monitor',
        step3: '3. Configure Settings',
        step3Desc: 'Configure sampling rate and monitoring metrics in the right panel',
        step4: '4. Start Monitoring',
        step4Desc: 'Click "Start Monitor" button to view real-time performance data',
        step5: '5. View Reports',
        step5Desc: 'After monitoring ends, view detailed data in the report page',
      },

      // Metrics description
      metrics: {
        title: 'Metrics Description',
        cpuTitle: 'CPU Usage',
        cpuDesc: 'Display application CPU usage percentage, including total CPU and app-specific CPU',

        memoryTitle: 'Memory Usage',
        memoryDesc: 'Display application memory usage, including PSS (Proportional Set Size)',

        fpsTitle: 'Frame Rate',
        fpsDesc: 'Display application frame rate for assessing UI smoothness',

        networkTitle: 'Network Traffic',
        networkDesc: 'Display network upload and download speeds',

        gpuTitle: 'GPU Usage',
        gpuDesc: 'Display GPU rendering usage',
        gpuNote: 'Note: Android GPU monitoring is not yet implemented, iOS is not supported due to system limitations',
      },

      // Platform Support
      platformSupport: {
        title: 'Platform Support',
        android: {
          title: 'Android Platform',
          osVersion: 'Supported OS: Android 7.0 and above',
          features: 'Supported Metrics: CPU, Memory, FPS, Network (Up/Down), Battery',
          gpuStatus: 'GPU Status: Not supported yet (In development)',
          notes: 'Note: USB Debugging mode must be enabled',
        },
        ios: {
          title: 'iOS Platform',
          osVersion: 'Supported OS: iOS 11.0 - 16.x only (iOS 17+ not supported)',
          features: 'Supported Metrics: CPU, Memory, FPS, Network (System-level), Battery',
          gpuStatus: 'GPU Status: Not supported',
          gpuReason: 'Reason:',
          gpuReason1: '• iOS system DVT channel cannot access GPU energy data',
          gpuReason2: '• CLI energy command times out (20+ seconds), not suitable for real-time monitoring',
          notes: 'Note: Requires trusting computer and enabling Developer Mode',
        },
      },

      // Alert features
      alertsFeature: {
        title: 'Alert Features',
        description: 'When performance metrics exceed set thresholds, the system automatically records alert information',
        fpsAlert: 'FPS Alert: Triggered when frame rate falls below the set value',
        memoryAlert: 'Memory Alert: Triggered when memory usage exceeds the set value',
        cpuAlert: 'CPU Alert: Triggered when CPU usage exceeds the set value',
        tempAlert: 'Temperature Alert: Triggered when device temperature exceeds the set value',
      },

      // Test reports
      reports: {
        title: 'Test Reports',
        description: 'After monitoring ends, view detailed performance data and charts in the report page',
        features: {
          charts: 'Visual Charts: Display performance curves for CPU, Memory, FPS, etc.',
          statistics: 'Statistics: Maximum, minimum, and average values',
          export: 'Export Function: Support exporting detailed reports in HTML format',
          comparison: 'Session Comparison: Support data comparison across multiple sessions',
        },
      },

      // About
      about: {
        version: 'Version',
        versionValue: '1.0.0',
        author: 'Author',
        authorValue: 'Aceyuan361',
        description: 'Insight Eye is a professional mobile device performance monitoring tool',
        features: 'Monitoring Capabilities',
        featuresList: 'Real-time CPU, Memory, FPS, Network performance monitoring',
        architecture: 'Technical Architecture',
        archDesc: 'Built with React + Vite + ECharts',
        license: 'License',
        licenseValue: 'MIT',
        projectName: 'Insight Eye',

        // Platform Support Details
        platformSupport: 'Platform Support',
        androidSection: 'Android Platform',
        androidVersion: 'Supported OS: Android 7.0+',
        androidFeatures: 'Metrics: CPU, Memory, FPS, Network (Up/Down), Battery',
        androidGpu: 'GPU: Not supported yet (In development)',
        iosSection: 'iOS Platform',
        iosVersion: 'Supported OS: iOS 11.0 - 16.x',
        iosFeatures: 'Metrics: CPU, Memory, FPS, Network (System-level), Battery',
        iosGpu: 'GPU: Not supported',
        iosGpuReason: 'Reason: iOS DVT limitation, cannot access GPU energy data',
      },
    },

    // === Statistics Panel ===
    stats: {
      max: 'Max',
      min: 'Min',
      avg: 'Avg',
      current: 'Current',
      title: 'Performance Statistics',
      selectSession: 'Please select a session',
      loading: 'Loading statistics...',
      network: 'Network',
      alerts: 'Alerts',
      noAlerts: 'No alert records',
      time: 'Time',
      value: 'Value',
    },

    // === Dialog Prompts ===
    dialogs: {
      confirmDelete: 'Confirm Delete',
      confirmDeleteMessage: 'Are you sure you want to delete the selected session(s)? This action cannot be undone.',
      confirmStop: 'Confirm Stop',
      confirmStopMessage: 'Are you sure you want to stop the current monitoring?',
      operationSuccess: 'Operation Successful',
      operationFailed: 'Operation Failed',
      invalidInput: 'Invalid Input',
      networkError: 'Network error, please check your connection',
    },

    // === Status ===
    status: {
      connecting: 'Connecting...',
      connected: 'Connected',
      disconnected: 'Disconnected',
      error: 'Error',
      success: 'Success',
      warning: 'Warning',
      info: 'Info',
    },
  },
};
