type EnvMap = Record<string, string | undefined>;

export function backendProxyUrl(env: EnvMap = runtimeEnv()): string {
  const configuredUrl = env.VITE_BACKEND_URL?.trim();
  return configuredUrl || "http://127.0.0.1:8000";
}

function runtimeEnv(): EnvMap {
  return ((globalThis as typeof globalThis & { process?: { env?: EnvMap } }).process?.env ?? {}) as EnvMap;
}
