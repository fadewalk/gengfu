import AISettings from "./ai-settings";

export default async function AISettingsPage() {
  return (
    <div className="flex flex-col gap-4">
      <div className="bg-white rounded-lg border p-6">
        <h2 className="text-lg font-semibold mb-2">AI 模型配置</h2>
        <p className="text-sm text-gray-500 mb-4">
          配置自定义 AI 模型端点，支持 OpenAI 兼容 API。配置后可在工作流中使用这些模型。
        </p>
      </div>
      <AISettings />
    </div>
  );
}
