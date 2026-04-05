import {
  CopilotRuntime,
  copilotRuntimeNextJSAppRouterEndpoint,
  ExperimentalEmptyAdapter,
} from "@copilotkit/runtime";
import { createOpenAI } from "@ai-sdk/openai";
import { NextRequest } from "next/server";
import { auth } from "@/auth";
import { getApiURL } from "@/utils/apiUrl";

async function initializeCopilotRuntime(req: NextRequest) {
  try {
    // Get the session to obtain the access token for backend authentication
    const session = await auth();

    if (!session?.accessToken) {
      console.error(
        "CopilotKit route: No session or access token available. " +
          "Make sure the user is logged in."
      );
      return null;
    }

    // Build the backend URL for the copilotkit config endpoint
    const apiUrl = getApiURL();
    const configUrl = `${apiUrl}/ai/copilotkit/config`;

    // Use the session access token to authenticate with the backend
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

    console.log(
      `CopilotKit config loaded: model=${config.model_name}, base_url=${config.base_url || "default"}`
    );

    // Use @ai-sdk/openai's createOpenAI and explicitly use .chat() to avoid
    // the Responses API (/v1/responses) which is not supported by third-party
    // OpenAI-compatible providers like MiniMax.
    const openai = createOpenAI({
      apiKey: config.api_key,
      ...(config.base_url ? { baseURL: config.base_url } : {}),
    });

    // Force chat completions API instead of the default Responses API
    const languageModel = openai.chat(config.model_name || "gpt-4o");

    // CopilotRuntime requires a serviceAdapter. We create a minimal one
    // that returns our configured language model.
    const serviceAdapter = new ExperimentalEmptyAdapter();

    const runtime = new CopilotRuntime();
    return { runtime, serviceAdapter: { ...serviceAdapter, getLanguageModel: () => languageModel } as any };
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
