"use client";
import { useI18n } from "@/i18n/hooks/useI18n";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  // This boundary replaces the root layout, including all of its providers.
  // Keep it independent of session, configuration, and API hooks.
  return (
    // 此边界替代根布局，i18n Provider 不在此树内，直接输出中文（更夫为中文优先发行版）
    <html lang="zh-CN">
      <body>
        <main>
          <h1>系统出错了</h1>
          <p>{error.message || "发生了意外错误。"}</p>
          {error.digest && <p>错误参考：{error.digest}</p>}
          <button onClick={reset}>重试</button>
        </main>
      </body>
    </html>
  );
}
