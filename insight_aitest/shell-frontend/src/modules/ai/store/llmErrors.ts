/**
 * LLM 错误码语义化：把 HTTP 状态 / error.code / 异常 message 映射成中文提示。
 *
 * 后端异常分类：
 * - LLMConfigError（key 缺失）→ 400
 * - LLMUnavailableError（超时/限流/空回复）→ 503
 * - openai AuthenticationError → 401
 * - openai BadRequestError（含 context length）→ 400
 * - openai RateLimitError → 429
 * 前端拿到的可能是：HTTP 状态码、SSE error 事件的 message、或 fetch 抛的异常。
 */

interface ParsedError {
  message: string;
  /** 是否可重试（超时/限流/空回复可重试；key 错误/参数错误不可重试） */
  retryable: boolean;
}

/** 从 SSE error 事件的原始 message 或 HTTP 文本提取语义化中文提示。 */
export function parseLLMError(raw: string | undefined | null, httpStatus?: number): ParsedError {
  const msg = (raw || '').toLowerCase();

  // 优先按 HTTP 状态码判断（最准）
  if (httpStatus === 401) {
    return { message: 'API Key 无效或已过期，请在设置中检查 Key 配置', retryable: false };
  }
  if (httpStatus === 403) {
    return { message: 'API Key 无权限访问该模型，请检查模型名或 Key 权限', retryable: false };
  }
  if (httpStatus === 404) {
    return { message: '模型不存在，请在设置中检查模型名是否正确', retryable: false };
  }
  if (httpStatus === 429) {
    return { message: '请求过于频繁或额度不足，请稍后重试', retryable: true };
  }
  if (httpStatus === 503 || httpStatus === 502 || httpStatus === 504) {
    return { message: '模型服务暂时不可用或响应超时，请稍后重试', retryable: true };
  }

  // 按消息关键词判断（SSE error 事件 / 异常 message）
  if (msg.includes('api key') || msg.includes('unauthorized') || msg.includes('invalid_api_key') || msg.includes('authentication')) {
    return { message: 'API Key 无效或已过期，请在设置中检查 Key 配置', retryable: false };
  }
  if (msg.includes('quota') || msg.includes('额度') || msg.includes('insufficient') || msg.includes('余额')) {
    return { message: 'API 额度不足，请充值或更换 Key', retryable: false };
  }
  if (msg.includes('rate_limit') || msg.includes('rate limit') || msg.includes('429') || msg.includes('频繁')) {
    return { message: '请求过于频繁，请稍后重试', retryable: true };
  }
  if (msg.includes('timeout') || msg.includes('超时') || msg.includes('timed out')) {
    return { message: '模型响应超时，请重试或降低思考级别', retryable: true };
  }
  if (msg.includes('context') && (msg.includes('length') || msg.includes('too long') || msg.includes('过长'))) {
    return { message: '对话内容过长超出模型上下文限制，请新建会话或精简内容', retryable: false };
  }
  if (msg.includes('maximum context') || msg.includes('token') && msg.includes('limit')) {
    return { message: '对话内容超出 token 上限，请新建会话或精简内容', retryable: false };
  }
  if (msg.includes('空回复') || msg.includes('empty')) {
    return { message: '模型返回为空，请重试或检查模型配置', retryable: true };
  }
  if (msg.includes('model') && (msg.includes('not found') || msg.includes('does not exist'))) {
    return { message: '模型不存在，请在设置中检查模型名', retryable: false };
  }
  if (msg.includes('connection') || msg.includes('econnrefused') || msg.includes('network') || msg.includes('fetch')) {
    return { message: '网络连接失败，请检查网络或 Base URL 配置', retryable: true };
  }

  // 兜底：返回原始消息（截断）
  return { message: raw ? (raw.length > 120 ? raw.slice(0, 120) + '...' : raw) : '请求失败', retryable: false };
}
