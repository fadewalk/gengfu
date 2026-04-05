import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import OpenAI from "openai";
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
