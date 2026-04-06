import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
  OpenAIAdapter,
} from "@copilotkit/runtime";
import { createOpenAI } from "@ai-sdk/openai";
import OpenAI from "openai";
import { NextRequest } from "next/server";
import { auth } from "@/auth";
import { getApiURL } from "@/utils/apiUrl";

async function initializeCopilotRuntime(req: NextRequest) {
  try {
    const session = await auth();

    if (!session?.accessToken) {
      console.error("CopilotKit route: No session or access token available.");
      return null;
    }

    const apiUrl = getApiURL();
    const configUrl = `${apiUrl}/ai/copilotkit/config`;

    const response = await fetch(configUrl, {
      headers: {
        Authorization: `Bearer ${session.accessToken}`,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(
        `Failed to fetch CopilotKit config from backend (${response.status}): ${errorText}`
      );
      return null;
    }

    const config = (await response.json()) as {
      base_url: string | null;
      api_key: string;
      model_name: string;
    };

    const modelName = config.model_name || "gpt-4o";

    console.log(
      `CopilotKit config: model=${modelName}, base_url=${config.base_url || "default"}`
    );

    // Create an OpenAI client for the service adapter's process() method.
    // This uses the standard chat.completions.stream() API.
    const openaiClient = new OpenAI({
      apiKey: config.api_key,
      ...(config.base_url ? { baseURL: config.base_url } : {}),
    });

    // Create an @ai-sdk/openai provider that uses .chat() to force
    // the /chat/completions endpoint instead of the default /responses
    // endpoint (which is not supported by third-party OpenAI-compatible
    // providers like MiniMax, Qwen, DeepSeek, GLM, etc.).
    const chatModel = createOpenAI({
      apiKey: config.api_key,
      ...(config.base_url ? { baseURL: config.base_url } : {}),
    }).chat(modelName);

    // Override getLanguageModel() to return the chat model so that
    // BuiltInAgent uses /chat/completions instead of /responses.
    const serviceAdapter = new OpenAIAdapter({
      openai: openaiClient,
      model: modelName,
    });

    (serviceAdapter as any).getLanguageModel = () => chatModel;

    const runtime = new CopilotRuntime();
    return { runtime, serviceAdapter };
  } catch (error) {
    console.error("Error initializing Copilot Runtime:", error);
    return null;
  }
}

export const POST = async (req: NextRequest) => {
  const runtimeOptions = await initializeCopilotRuntime(req);

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
