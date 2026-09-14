/** 把 unknown 异常安全转为用户可读文案（catch (e) 后请用这个替代 any 断言）。 */
export function errorMessage(e: unknown, fallback = ''): string {
  if (e instanceof Error && e.message) return e.message;
  if (typeof e === 'string' && e) return e;
  return fallback;
}
