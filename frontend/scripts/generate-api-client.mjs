import { writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, "..");
const outputPath = resolve(projectRoot, "src/lib/api.generated.ts");
const openapiUrl = process.env.SUTRA_OPENAPI_URL ?? "http://127.0.0.1:8001/openapi.json";

async function loadSchema(url) {
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(`Failed to load OpenAPI schema from ${url}: ${response.status}`);
  }
  return response.json();
}

const schema = await loadSchema(openapiUrl);
const generatedTypes = astToString(await openapiTS(schema)).trimEnd();

function toCamelCase(value) {
  return value
    .split("_")
    .filter(Boolean)
    .map((part, index) =>
      index === 0
        ? part.toLowerCase()
        : part.charAt(0).toUpperCase() + part.slice(1).toLowerCase(),
    )
    .join("");
}

const methodOrder = ["get", "post", "put", "patch", "delete"];
const seenMethodNames = new Set();
const generatedClientMethods = [];

for (const [path, pathItem] of Object.entries(schema.paths ?? {})) {
  for (const method of methodOrder) {
    const operation = pathItem?.[method];
    if (!operation) {
      continue;
    }
    const operationId = operation.operationId ?? `${method}_${path.replace(/[^a-zA-Z0-9]+/g, "_")}`;
    const baseName = operationId.split("_api_")[0] ?? operationId;
    let methodName = toCamelCase(baseName);
    if (!methodName) {
      methodName = `${method.toLowerCase()}${toCamelCase(path.replace(/[^a-zA-Z0-9]+/g, "_"))}`;
    }
    if (seenMethodNames.has(methodName)) {
      methodName = `${methodName}${method.toUpperCase()}`;
    }
    if (methodName === "streamConversationEvents") {
      continue;
    }
    seenMethodNames.add(methodName);
    generatedClientMethods.push({
      name: methodName,
      method: method.toUpperCase(),
      path,
    });
  }
}

const clientMethodsSource = generatedClientMethods
  .map((entry) => {
    const methodLower = entry.method.toLowerCase();
    const escapedPath = entry.path.replace(/"/g, '\\"');
    return `    ${entry.name}: (init?: any): Promise<[MethodResponse<Client<paths>, "${methodLower}", "${escapedPath}">] extends [never] ? unknown : MethodResponse<Client<paths>, "${methodLower}", "${escapedPath}">> => {
      if (init === undefined) {
        return requestData((client.${entry.method} as any)("${escapedPath}"));
      }
      return requestData((client.${entry.method} as any)("${escapedPath}", init));
    },`;
  })
  .join("\n");
const source = `import createClient, { type Client, type MethodResponse, type Middleware } from "openapi-fetch";

${generatedTypes}

type Schema<T extends keyof components["schemas"]> = components["schemas"][T];

export type SessionPayload = Schema<"AuthMeResponse">;
export type Team = Schema<"TeamRead">;
export type Agent = Omit<Schema<"AgentRead">, "team_ids"> & {
  team_ids: string[];
};
export type RoleTemplate = Schema<"RoleTemplateRead">;
export type ChatMessage = Schema<"MessageRead">;
export type SharedWorkspaceItem = Schema<"SharedWorkspaceItemRead">;
export type Artifact = Schema<"ArtifactRead">;
export type AutomationJob = Schema<"AutomationJobRead">;
export type AgentResponseRequestBody = Omit<Schema<"AgentResponseCreateRequest">, "store" | "model"> & {
  store?: Schema<"AgentResponseCreateRequest">["store"];
  model?: Schema<"AgentResponseCreateRequest">["model"];
};
export type SecretCreateRequestBody = Omit<Schema<"SecretCreateRequest">, "scope"> & {
  scope?: Schema<"SecretCreateRequest">["scope"];
};
export type AutomationJobCreateRequestBody = Omit<Schema<"AutomationJobCreateRequest">, "enabled"> & {
  enabled?: Schema<"AutomationJobCreateRequest">["enabled"];
};

export type ConversationStreamEvent = {
  event_id: string;
  type: string;
  conversation_id: string;
  agent_id?: string | null;
  timestamp: string;
  sequence: number;
  payload: Record<string, unknown>;
};

export type ConversationStreamHandlers = {
  onEvent: (event: ConversationStreamEvent) => void;
  onError?: (error: Error) => void;
};

export type ConversationStreamSubscription = {
  close: () => void;
  done: Promise<void>;
};

export type ApiClientOptions = {
  baseUrl: string;
  getAccessToken: () => Promise<string | null>;
  fetcher?: typeof fetch;
};

type ApiResult = {
  data?: unknown;
  error?: unknown;
  response: Response;
};

export type ApiClient = ReturnType<typeof createApiClient>;

function extractErrorMessage(result: ApiResult): string {
  if (result.error && typeof result.error === "object") {
    if ("detail" in result.error) {
      return String((result.error as { detail: unknown }).detail);
    }
    if ("message" in result.error) {
      return String((result.error as { message: unknown }).message);
    }
  }
  return \`Request failed with \${result.response.status}\`;
}

export async function requestData<T extends Promise<ApiResult>>(
  request: T,
): Promise<NonNullable<Awaited<T>["data"]>> {
  const result = await request;
  if (result.error !== undefined) {
    throw new Error(extractErrorMessage(result));
  }
  return result.data as NonNullable<Awaited<T>["data"]>;
}

function resolveFetch(fetcher?: typeof fetch) {
  if (!fetcher) {
    return undefined;
  }
  return (request: Request) => fetcher(request);
}

export function createApiClient(options: ApiClientOptions) {
  const client: Client<paths> = createClient<paths>({
    baseUrl: options.baseUrl,
    fetch: resolveFetch(options.fetcher),
  });

  const authMiddleware: Middleware = {
    async onRequest({ request }) {
      const token = await options.getAccessToken();
      if (!request.headers.has("Accept")) {
        request.headers.set("Accept", "application/json");
      }
      if (token) {
        request.headers.set("Authorization", \`Bearer \${token}\`);
      }
      return request;
    },
  };

  client.use(authMiddleware);

  const fetcher = options.fetcher ?? fetch;

  async function streamConversationEvents(
    conversationId: string,
    handlers: ConversationStreamHandlers,
  ): Promise<ConversationStreamSubscription> {
    const controller = new AbortController();
    const token = await options.getAccessToken();
    const headers = new Headers();
    headers.set("Accept", "text/event-stream");
    if (token) {
      headers.set("Authorization", \`Bearer \${token}\`);
    }

    const done = (async () => {
      try {
        const response = await fetcher(
          \`\${options.baseUrl}/api/conversations/\${conversationId}/stream\`,
          {
            method: "GET",
            headers,
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          throw new Error(\`Request failed with \${response.status}\`);
        }
        if (!response.body) {
          throw new Error("Streaming response body was empty.");
        }

        const decoder = new TextDecoder();
        const reader = response.body.getReader();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const segments = buffer.split("\\n\\n");
          buffer = segments.pop() ?? "";

          for (const segment of segments) {
            const dataLine = segment
              .split("\\n")
              .find((line) => line.startsWith("data: "));
            if (!dataLine) {
              continue;
            }
            handlers.onEvent(JSON.parse(dataLine.slice(6)) as ConversationStreamEvent);
          }
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }
        handlers.onError?.(
          error instanceof Error ? error : new Error("Conversation stream failed."),
        );
      }
    })();

    return {
      close: () => controller.abort(),
      done,
    };
  }

  return Object.assign(client, {
${clientMethodsSource}
    streamConversationEvents,
  });
}
`;

writeFileSync(
  outputPath,
  `${source}\n`,
  "utf8",
);

console.log(`Fetched ${openapiUrl}`);
console.log(`Wrote ${outputPath}`);
