import { useI18n } from "@/i18n/hooks/useI18n";
import { Card, Text } from "@tremor/react";
import Image from "next/image";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";

export const metadata = {
  title: "更夫 Gengfu",
  description: "开源的告警聚合与 AI 事件管理平台 —— 监控交给夜莺们，告警之后的事交给更夫。",
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const messages = await getMessages();

  return (
    <html lang="en" className="bg-tremor-background-subtle">
      <body>
        <NextIntlClientProvider messages={messages}>
          <div className="min-h-screen flex items-center justify-center bg-tremor-background-subtle p-4">
            <div className="flex flex-col items-center gap-6">
              <div className="flex items-center gap-3">
                <Text className="text-3xl font-bold text-orange-500">
                  Keep
                </Text>
              </div>
              <Card
                className="w-full max-w-md p-8 min-w-96 flex flex-col gap-6 items-center"
                decoration="top"
                decorationColor="orange"
              >
                {children}
              </Card>
            </div>
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
