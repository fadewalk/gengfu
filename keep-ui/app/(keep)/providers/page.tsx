import { useI18n } from "@/i18n/hooks/useI18n";
import ProvidersPage from "./page.client";

export default async function Page(props: {
  searchParams?: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const searchParams = await props.searchParams;
  return <ProvidersPage searchParams={searchParams} />;
}

export const metadata = {
  title: "Keep - 集成",
  description: "连接集成到 Keep，让告警更智能。",
};
