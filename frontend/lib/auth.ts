/** Token persistence in localStorage (guarded for SSR). */

const ACCESS_KEY = "da_access";
const REFRESH_KEY = "da_refresh";

const hasWindow = () => typeof window !== "undefined";

export const tokenStore = {
  getAccess(): string | null {
    return hasWindow() ? window.localStorage.getItem(ACCESS_KEY) : null;
  },
  getRefresh(): string | null {
    return hasWindow() ? window.localStorage.getItem(REFRESH_KEY) : null;
  },
  set(access: string, refresh: string): void {
    if (!hasWindow()) return;
    window.localStorage.setItem(ACCESS_KEY, access);
    window.localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear(): void {
    if (!hasWindow()) return;
    window.localStorage.removeItem(ACCESS_KEY);
    window.localStorage.removeItem(REFRESH_KEY);
  },
};
