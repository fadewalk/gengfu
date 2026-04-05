import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import OpenAI from "openai";
import { NextRequest } from "next/server";
import { createServerApiClient } from "@/shared/api/server";

async function initializeCopilotRuntime() {
  try {
    const apiClient = await createServerApiClient();

    // Fetch OpenAI-compatible config from backend AI model settings
    const config = await apiClient.get<{
      base_url: string | null;
      api_key: string;
      model_name: string;
    }>("/ai/copilotkit/config");

    const openai = new OpenAI({
      apiKey: config.api_key,
      ...(config.base_url ? { baseURL: config.base_url } : {}),
    });
    const serviceAdapter = new OpenAIAdapter({
      openai,
      ...(config.model_name ? { model: config.model_name } : {}),
    });
    const runtime = new CopilotRuntime();
    return { runtime, serviceAdapter };
  } catch (error) {
    console.error("Error initializing Copilot Runtime:", error);
    return null;
  }
}

export const POST = async (req: NextRequest) => {
  const runtimeOptions = await initializeCopilotRuntime();

  if (!runtimeOptions) {
    return new Response("Error initializing Copilot Runtime", { status: 500 });
  }
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime: runtimeOptions.runtime,
    serviceAdapter: runtimeOptions.serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
