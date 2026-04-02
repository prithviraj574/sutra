import createClient, { type Client, type MethodResponse, type Middleware } from "openapi-fetch";

export interface paths {
    "/api/health": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Healthcheck */
        get: operations["healthcheck_api_health_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/github": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Start Github Oauth */
        get: operations["start_github_oauth_api_auth_github_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/github/connection": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Github Connection */
        get: operations["read_github_connection_api_auth_github_connection_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/github/callback": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Complete Github Oauth */
        get: operations["complete_github_oauth_api_auth_github_callback_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Read Current User */
        get: operations["read_current_user_api_auth_me_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Jobs */
        get: operations["get_jobs_api_jobs_get"];
        put?: never;
        /** Post Job */
        post: operations["post_job_api_jobs_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/jobs/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Patch Job */
        patch: operations["patch_job_api_jobs__job_id__patch"];
        trace?: never;
    };
    "/api/jobs/{job_id}/run": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Run Job */
        post: operations["post_run_job_api_jobs__job_id__run_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/github/repositories": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Github Repositories */
        get: operations["get_github_repositories_api_github_repositories_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/github/teams/{team_id}/workspace/items/{item_id}/export": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Export Workspace Item */
        post: operations["export_workspace_item_api_github_teams__team_id__workspace_items__item_id__export_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/teams": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Teams */
        get: operations["list_teams_api_teams_get"];
        put?: never;
        /** Create Team */
        post: operations["create_team_api_teams_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/role-templates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Role Templates */
        get: operations["get_role_templates_api_role_templates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/teams/{team_id}/workspace": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Team Workspace */
        get: operations["get_team_workspace_api_teams__team_id__workspace_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/teams/{team_id}/artifacts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Team Artifacts */
        get: operations["get_team_artifacts_api_teams__team_id__artifacts_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/teams/{team_id}/workspace/items": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Workspace Item */
        post: operations["create_workspace_item_api_teams__team_id__workspace_items_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/teams/{team_id}/conversations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Team Conversations */
        get: operations["get_team_conversations_api_teams__team_id__conversations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/teams/{team_id}/tasks": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Team Tasks */
        get: operations["get_team_tasks_api_teams__team_id__tasks_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/teams/{team_id}/inbox/run-cycle": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Run Team Inbox Cycle */
        post: operations["post_run_team_inbox_cycle_api_teams__team_id__inbox_run_cycle_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/teams/{team_id}/huddles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Team Huddle */
        post: operations["create_team_huddle_api_teams__team_id__huddles_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/teams/{team_id}/agents/{agent_id}/responses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Team Member Response */
        post: operations["create_team_member_response_api_teams__team_id__agents__agent_id__responses_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/teams/{team_id}/responses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Team Response */
        post: operations["create_team_response_api_teams__team_id__responses_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agents": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Agents */
        get: operations["list_agents_api_agents_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agents/{agent_id}/conversations": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Agent Conversations */
        get: operations["get_agent_conversations_api_agents__agent_id__conversations_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agents/{agent_id}/inbox": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Agent Inbox */
        get: operations["get_agent_inbox_api_agents__agent_id__inbox_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agents/{agent_id}/inbox/claim-next": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Claim Next Inbox Task */
        post: operations["post_claim_next_inbox_task_api_agents__agent_id__inbox_claim_next_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agents/{agent_id}/inbox/run-next": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Run Next Inbox Task */
        post: operations["post_run_next_inbox_task_api_agents__agent_id__inbox_run_next_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agents/{agent_id}/responses": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Agent Response */
        post: operations["create_agent_response_api_agents__agent_id__responses_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/tasks/{task_id}/updates": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Task Updates */
        get: operations["get_task_updates_api_tasks__task_id__updates_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/tasks/{task_id}/delegate": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Task Delegate */
        post: operations["post_task_delegate_api_tasks__task_id__delegate_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/tasks/{task_id}/reports": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Task Report */
        post: operations["post_task_report_api_tasks__task_id__reports_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/tasks/{task_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Task Message */
        post: operations["post_task_message_api_tasks__task_id__messages_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/tasks/{task_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Post Task Complete */
        post: operations["post_task_complete_api_tasks__task_id__complete_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/conversations/{conversation_id}/messages": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Conversation Messages */
        get: operations["get_conversation_messages_api_conversations__conversation_id__messages_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/conversations/{conversation_id}/stream": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Stream Conversation Events */
        get: operations["stream_conversation_events_api_conversations__conversation_id__stream_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/secrets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Secrets */
        get: operations["list_secrets_api_secrets_get"];
        put?: never;
        /** Create Secret */
        post: operations["create_secret_api_secrets_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/secrets/{secret_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        /** Remove Secret */
        delete: operations["remove_secret_api_secrets__secret_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agents/{agent_id}/runtime": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Agent Runtime */
        get: operations["get_agent_runtime_api_agents__agent_id__runtime_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agents/{agent_id}/runtime/provision": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Provision Agent Runtime */
        post: operations["provision_agent_runtime_api_agents__agent_id__runtime_provision_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agents/{agent_id}/runtime/verify": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Verify Agent Runtime */
        post: operations["verify_agent_runtime_api_agents__agent_id__runtime_verify_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/agents/{agent_id}/runtime/restart": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Restart Agent Runtime */
        post: operations["restart_agent_runtime_api_agents__agent_id__runtime_restart_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/system/poller": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Poller Status */
        get: operations["get_poller_status_api_system_poller_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/healthz": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Healthz */
        get: operations["healthz_healthz_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AgentInboxClaimResponse */
        AgentInboxClaimResponse: {
            task?: components["schemas"]["TeamTaskRead"] | null;
        };
        /** AgentInboxRunResponse */
        AgentInboxRunResponse: {
            task?: components["schemas"]["TeamTaskRead"] | null;
            /** Conversation Id */
            conversation_id?: string | null;
            /** Response Id */
            response_id?: string | null;
            /** Output Text */
            output_text?: string | null;
            /** Workspace Item Id */
            workspace_item_id?: string | null;
        };
        /** AgentListResponse */
        AgentListResponse: {
            /** Items */
            items: components["schemas"]["AgentRead"][];
        };
        /** AgentRead */
        AgentRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
            /** Team Ids */
            team_ids?: string[];
            /** Role Template Id */
            role_template_id?: string | null;
            /** Name */
            name: string;
            /** Role Name */
            role_name: string;
            status: components["schemas"]["AgentStatus"];
            runtime_kind: components["schemas"]["RuntimeKind"];
            /** Hermes Home Uri */
            hermes_home_uri?: string | null;
            /** Private Volume Uri */
            private_volume_uri?: string | null;
            /** Shared Workspace Enabled */
            shared_workspace_enabled: boolean;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** AgentResponseCreateRequest */
        AgentResponseCreateRequest: {
            /** Input */
            input: string | {
                [key: string]: unknown;
            }[];
            /** Instructions */
            instructions?: string | null;
            /** Conversation Id */
            conversation_id?: string | null;
            /** Previous Response Id */
            previous_response_id?: string | null;
            /**
             * Store
             * @default true
             */
            store: boolean;
            /**
             * Model
             * @default hermes-agent
             */
            model: string;
            /** Metadata */
            metadata?: {
                [key: string]: unknown;
            };
            /** Secret Ids */
            secret_ids?: string[];
        };
        /** AgentResponseCreateResponse */
        AgentResponseCreateResponse: {
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /** Response Id */
            response_id: string;
            /** Output Text */
            output_text: string;
            /** Raw Response */
            raw_response: {
                [key: string]: unknown;
            };
            /** Workspace Item Id */
            workspace_item_id?: string | null;
        };
        /**
         * AgentStatus
         * @enum {string}
         */
        AgentStatus: "provisioning" | "ready" | "running" | "runtime_unreachable";
        /**
         * ArtifactKind
         * @enum {string}
         */
        ArtifactKind: "document" | "github_export";
        /** ArtifactRead */
        ArtifactRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Team Id */
            team_id?: string | null;
            /** Conversation Id */
            conversation_id?: string | null;
            /** Agent Id */
            agent_id?: string | null;
            /** Name */
            name: string;
            kind: components["schemas"]["ArtifactKind"];
            /** Uri */
            uri: string;
            /** Mime Type */
            mime_type?: string | null;
            /** Preview Uri */
            preview_uri?: string | null;
            /** Github Repo */
            github_repo?: string | null;
            /** Github Branch */
            github_branch?: string | null;
            /** Github Sha */
            github_sha?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** AuthMeResponse */
        AuthMeResponse: {
            user: components["schemas"]["UserRead"];
        };
        /** AutomationJobCreateRequest */
        AutomationJobCreateRequest: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Agent Team Id */
            agent_team_id?: string | null;
            /** Name */
            name: string;
            /** Schedule */
            schedule: string;
            /** Prompt */
            prompt: string;
            /**
             * Enabled
             * @default true
             */
            enabled: boolean;
        };
        /** AutomationJobListResponse */
        AutomationJobListResponse: {
            /** Items */
            items: components["schemas"]["AutomationJobRead"][];
        };
        /** AutomationJobRead */
        AutomationJobRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Agent Team Id */
            agent_team_id?: string | null;
            /** Name */
            name: string;
            /** Schedule */
            schedule: string;
            /** Prompt */
            prompt: string;
            /** Enabled */
            enabled: boolean;
            /** Last Run At */
            last_run_at?: string | null;
            /** Next Run At */
            next_run_at?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** AutomationJobResponse */
        AutomationJobResponse: {
            job: components["schemas"]["AutomationJobRead"];
        };
        /** AutomationJobRunResponse */
        AutomationJobRunResponse: {
            job: components["schemas"]["AutomationJobRead"];
            /** Conversation Id */
            conversation_id?: string | null;
            /** Response Id */
            response_id?: string | null;
            /** Output Text */
            output_text?: string | null;
            /** Workspace Item Id */
            workspace_item_id?: string | null;
            /**
             * Generated Items
             * @default []
             */
            generated_items: components["schemas"]["SharedWorkspaceItemRead"][];
        };
        /** AutomationJobUpdateRequest */
        AutomationJobUpdateRequest: {
            /** Name */
            name?: string | null;
            /** Schedule */
            schedule?: string | null;
            /** Prompt */
            prompt?: string | null;
            /** Enabled */
            enabled?: boolean | null;
        };
        /** ConversationListResponse */
        ConversationListResponse: {
            /** Items */
            items: components["schemas"]["ConversationRead"][];
        };
        /**
         * ConversationMode
         * @enum {string}
         */
        ConversationMode: "agent" | "team" | "team_huddle" | "team_member";
        /** ConversationRead */
        ConversationRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Agent Team Id */
            agent_team_id?: string | null;
            /** Agent Id */
            agent_id?: string | null;
            mode: components["schemas"]["ConversationMode"];
            /** Latest Response Id */
            latest_response_id?: string | null;
            status: components["schemas"]["ConversationStatus"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * ConversationStatus
         * @enum {string}
         */
        ConversationStatus: "active";
        /**
         * GitHubAccountType
         * @enum {string}
         */
        GitHubAccountType: "user" | "organization";
        /** GitHubConnectionRead */
        GitHubConnectionRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
            /** Installation Id */
            installation_id: string;
            /** Account Login */
            account_login: string;
            account_type: components["schemas"]["GitHubAccountType"];
            /**
             * Connected At
             * Format: date-time
             */
            connected_at: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** GitHubConnectionStatusResponse */
        GitHubConnectionStatusResponse: {
            connection: components["schemas"]["GitHubConnectionRead"] | null;
        };
        /** GitHubExportRequest */
        GitHubExportRequest: {
            /** Repository Full Name */
            repository_full_name: string;
            /** Path */
            path: string;
            /** Branch */
            branch?: string | null;
            /** Commit Message */
            commit_message: string;
        };
        /** GitHubExportResponse */
        GitHubExportResponse: {
            /**
             * Artifact Id
             * Format: uuid
             */
            artifact_id: string;
            artifact: components["schemas"]["ArtifactRead"];
            item: components["schemas"]["SharedWorkspaceItemRead"];
            /** Repository Full Name */
            repository_full_name: string;
            /** Branch */
            branch: string;
            /** Commit Sha */
            commit_sha: string;
            /** Content Url */
            content_url: string;
            /** Commit Url */
            commit_url: string;
        };
        /** GitHubRepositoryListResponse */
        GitHubRepositoryListResponse: {
            /** Items */
            items: components["schemas"]["GitHubRepositoryRead"][];
        };
        /** GitHubRepositoryRead */
        GitHubRepositoryRead: {
            /** Id */
            id: number;
            /** Name */
            name: string;
            /** Full Name */
            full_name: string;
            /** Default Branch */
            default_branch: string;
            /** Private */
            private: boolean;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /**
         * MessageActorType
         * @enum {string}
         */
        MessageActorType: "user" | "assistant" | "system";
        /** MessageListResponse */
        MessageListResponse: {
            /** Items */
            items: components["schemas"]["MessageRead"][];
        };
        /** MessageRead */
        MessageRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            actor_type: components["schemas"]["MessageActorType"];
            /** Actor Id */
            actor_id?: string | null;
            /** Content */
            content: string;
            /** Response Chain Id */
            response_chain_id?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** PollerLeaseRead */
        PollerLeaseRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Owner Id */
            owner_id?: string | null;
            state: components["schemas"]["PollerLeaseState"];
            /** Last Heartbeat At */
            last_heartbeat_at?: string | null;
            /** Lease Expires At */
            lease_expires_at?: string | null;
            /** Last Sweep Started At */
            last_sweep_started_at?: string | null;
            /** Last Sweep Completed At */
            last_sweep_completed_at?: string | null;
            /** Last Executed Count */
            last_executed_count: number;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * PollerLeaseState
         * @enum {string}
         */
        PollerLeaseState: "idle" | "running";
        /** PollerStatusResponse */
        PollerStatusResponse: {
            /** Enabled */
            enabled: boolean;
            /** Interval Seconds */
            interval_seconds: number;
            /** Lease Seconds */
            lease_seconds: number;
            /** Max Tasks Per Sweep */
            max_tasks_per_sweep: number;
            /** Is Active */
            is_active: boolean;
            lease?: components["schemas"]["PollerLeaseRead"] | null;
        };
        /** RoleTemplateListResponse */
        RoleTemplateListResponse: {
            /** Items */
            items: components["schemas"]["RoleTemplateRead"][];
        };
        /** RoleTemplateRead */
        RoleTemplateRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Key */
            key: string;
            /** Name */
            name: string;
            /** Description */
            description?: string | null;
            /** Default System Prompt */
            default_system_prompt: string;
            default_tool_profile: components["schemas"]["ToolProfile"];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * RuntimeKind
         * @enum {string}
         */
        RuntimeKind: "firecracker";
        /** RuntimeLeaseRead */
        RuntimeLeaseRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Vm Id */
            vm_id: string;
            /** Host Vm Id */
            host_vm_id?: string | null;
            /** Host Api Base Url */
            host_api_base_url?: string | null;
            state: components["schemas"]["RuntimeLeaseState"];
            /** Provider */
            provider: string;
            /** Api Base Url */
            api_base_url?: string | null;
            /** Last Heartbeat At */
            last_heartbeat_at?: string | null;
            /** Started At */
            started_at?: string | null;
            /** Ready */
            ready: boolean;
            /** Heartbeat Fresh */
            heartbeat_fresh: boolean;
            /** Readiness Stage */
            readiness_stage: string;
            /** Readiness Reason */
            readiness_reason: string;
            /** Probe Detail */
            probe_detail?: string | null;
            /** Probe Checked Url */
            probe_checked_url?: string | null;
            /** Isolation Ok */
            isolation_ok: boolean;
            /** Isolation Reason */
            isolation_reason: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** RuntimeLeaseResponse */
        RuntimeLeaseResponse: {
            lease: components["schemas"]["RuntimeLeaseRead"];
        };
        /**
         * RuntimeLeaseState
         * @enum {string}
         */
        RuntimeLeaseState: "provisioning" | "running" | "unreachable";
        /** SecretCreateRequest */
        SecretCreateRequest: {
            /** Name */
            name: string;
            /** Value */
            value: string;
            /** Provider */
            provider?: string | null;
            /** @default user */
            scope: components["schemas"]["SecretScope"];
            /** Team Id */
            team_id?: string | null;
            /** Agent Id */
            agent_id?: string | null;
        };
        /** SecretCreateResponse */
        SecretCreateResponse: {
            secret: components["schemas"]["SecretRead"];
        };
        /** SecretDeleteResponse */
        SecretDeleteResponse: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Deleted */
            deleted: boolean;
        };
        /** SecretListResponse */
        SecretListResponse: {
            /** Items */
            items: components["schemas"]["SecretRead"][];
        };
        /** SecretRead */
        SecretRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
            /** Team Id */
            team_id?: string | null;
            /** Agent Id */
            agent_id?: string | null;
            /** Name */
            name: string;
            /** Provider */
            provider?: string | null;
            scope: components["schemas"]["SecretScope"];
            /** Last Used At */
            last_used_at?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * SecretScope
         * @enum {string}
         */
        SecretScope: "user" | "team" | "agent";
        /** SharedWorkspaceItemRead */
        SharedWorkspaceItemRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Team Id
             * Format: uuid
             */
            team_id: string;
            /** Path */
            path: string;
            kind: components["schemas"]["WorkspaceItemKind"];
            /** Size Bytes */
            size_bytes?: number | null;
            /** Content Text */
            content_text?: string | null;
            /** Conversation Id */
            conversation_id?: string | null;
            /** Agent Id */
            agent_id?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** TeamAgentCreate */
        TeamAgentCreate: {
            /** Role Template Key */
            role_template_key: string;
            /** Name */
            name?: string | null;
        };
        /** TeamArtifactListResponse */
        TeamArtifactListResponse: {
            /** Items */
            items: components["schemas"]["ArtifactRead"][];
        };
        /** TeamConversationListResponse */
        TeamConversationListResponse: {
            /** Items */
            items: components["schemas"]["ConversationRead"][];
        };
        /** TeamCreateRequest */
        TeamCreateRequest: {
            /** Name */
            name: string;
            /** Description */
            description?: string | null;
            /** Agents */
            agents: components["schemas"]["TeamAgentCreate"][];
        };
        /** TeamCreateResponse */
        TeamCreateResponse: {
            team: components["schemas"]["TeamRead"];
            /** Agents */
            agents: components["schemas"]["AgentRead"][];
        };
        /** TeamHuddleCreateRequest */
        TeamHuddleCreateRequest: {
            /** Input */
            input: string | {
                [key: string]: unknown;
            }[];
            /** Conversation Id */
            conversation_id?: string | null;
            /** Instructions */
            instructions?: string | null;
            /** Secret Ids */
            secret_ids?: string[];
        };
        /** TeamHuddleCreateResponse */
        TeamHuddleCreateResponse: {
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /** Output Text */
            output_text: string;
            /** Outputs */
            outputs: components["schemas"]["TeamMemberResponseRead"][];
            /** Tasks */
            tasks: components["schemas"]["TeamTaskRead"][];
            /** Workspace Item Id */
            workspace_item_id?: string | null;
        };
        /** TeamInboxCycleItemRead */
        TeamInboxCycleItemRead: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            task?: components["schemas"]["TeamTaskRead"] | null;
            /** Conversation Id */
            conversation_id?: string | null;
            /** Response Id */
            response_id?: string | null;
            /** Output Text */
            output_text?: string | null;
            /** Workspace Item Id */
            workspace_item_id?: string | null;
        };
        /** TeamInboxCycleResponse */
        TeamInboxCycleResponse: {
            /** Executed Count */
            executed_count: number;
            /** Results */
            results: components["schemas"]["TeamInboxCycleItemRead"][];
        };
        /** TeamListResponse */
        TeamListResponse: {
            /** Items */
            items: components["schemas"]["TeamRead"][];
        };
        /** TeamMemberResponseRead */
        TeamMemberResponseRead: {
            /**
             * Agent Id
             * Format: uuid
             */
            agent_id: string;
            /** Agent Name */
            agent_name: string;
            /** Role Name */
            role_name: string;
            /** Response Id */
            response_id: string;
            /** Output Text */
            output_text: string;
        };
        /**
         * TeamMode
         * @enum {string}
         */
        TeamMode: "personal" | "team";
        /** TeamRead */
        TeamRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * User Id
             * Format: uuid
             */
            user_id: string;
            /** Name */
            name: string;
            /** Description */
            description?: string | null;
            mode: components["schemas"]["TeamMode"];
            /** Shared Workspace Uri */
            shared_workspace_uri?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** TeamResponseCreateRequest */
        TeamResponseCreateRequest: {
            /** Input */
            input: string | {
                [key: string]: unknown;
            }[];
            /** Conversation Id */
            conversation_id?: string | null;
            /** Instructions */
            instructions?: string | null;
            /** Secret Ids */
            secret_ids?: string[];
        };
        /** TeamResponseCreateResponse */
        TeamResponseCreateResponse: {
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /** Output Text */
            output_text: string;
            /** Outputs */
            outputs: components["schemas"]["TeamMemberResponseRead"][];
            /** Workspace Item Id */
            workspace_item_id?: string | null;
            /** Generated Items */
            generated_items?: components["schemas"]["SharedWorkspaceItemRead"][];
        };
        /** TeamTaskCompleteRequest */
        TeamTaskCompleteRequest: {
            /** Content */
            content: string;
            /** Agent Id */
            agent_id?: string | null;
            /** Claim Token */
            claim_token?: string | null;
        };
        /** TeamTaskDelegateRequest */
        TeamTaskDelegateRequest: {
            /**
             * Assigned Agent Id
             * Format: uuid
             */
            assigned_agent_id: string;
            /** Note */
            note?: string | null;
        };
        /** TeamTaskListResponse */
        TeamTaskListResponse: {
            /** Items */
            items: components["schemas"]["TeamTaskRead"][];
        };
        /** TeamTaskMessageRequest */
        TeamTaskMessageRequest: {
            /** Content */
            content: string;
            /** Agent Id */
            agent_id?: string | null;
        };
        /** TeamTaskMutationResponse */
        TeamTaskMutationResponse: {
            task: components["schemas"]["TeamTaskRead"];
        };
        /** TeamTaskRead */
        TeamTaskRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Team Id
             * Format: uuid
             */
            team_id: string;
            /**
             * Conversation Id
             * Format: uuid
             */
            conversation_id: string;
            /**
             * Assigned Agent Id
             * Format: uuid
             */
            assigned_agent_id: string;
            /** Title */
            title: string;
            /** Instruction */
            instruction: string;
            status: components["schemas"]["TeamTaskStatus"];
            source: components["schemas"]["TeamTaskSource"];
            /** Claim Token */
            claim_token?: string | null;
            /** Claimed At */
            claimed_at?: string | null;
            /** Claim Expires At */
            claim_expires_at?: string | null;
            /** Completed At */
            completed_at?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** TeamTaskReportRequest */
        TeamTaskReportRequest: {
            /** Content */
            content: string;
            /** Agent Id */
            agent_id?: string | null;
        };
        /**
         * TeamTaskSource
         * @enum {string}
         */
        TeamTaskSource: "huddle";
        /**
         * TeamTaskStatus
         * @enum {string}
         */
        TeamTaskStatus: "open" | "in_progress" | "claimed" | "completed";
        /** TeamTaskUpdateListResponse */
        TeamTaskUpdateListResponse: {
            /** Items */
            items: components["schemas"]["TeamTaskUpdateRead"][];
        };
        /** TeamTaskUpdateRead */
        TeamTaskUpdateRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Task Id
             * Format: uuid
             */
            task_id: string;
            /**
             * Team Id
             * Format: uuid
             */
            team_id: string;
            /** Agent Id */
            agent_id?: string | null;
            event_type: components["schemas"]["TeamTaskUpdateType"];
            /** Content */
            content: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * TeamTaskUpdateType
         * @enum {string}
         */
        TeamTaskUpdateType: "reported" | "message" | "completed" | "delegated" | "claimed" | "released" | "reopened";
        /** TeamWorkspaceResponse */
        TeamWorkspaceResponse: {
            team: components["schemas"]["TeamRead"];
            /** Items */
            items: components["schemas"]["SharedWorkspaceItemRead"][];
        };
        /**
         * ToolProfile
         * @enum {string}
         */
        ToolProfile: "full_web";
        /** UserRead */
        UserRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Firebase Uid */
            firebase_uid: string;
            /** Email */
            email: string;
            /** Display Name */
            display_name?: string | null;
            /** Photo Url */
            photo_url?: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
        /**
         * WorkspaceItemKind
         * @enum {string}
         */
        WorkspaceItemKind: "file" | "directory";
        /** WorkspaceItemUpsertRequest */
        WorkspaceItemUpsertRequest: {
            /** Path */
            path: string;
            /** @default file */
            kind: components["schemas"]["WorkspaceItemKind"];
            /** Content Text */
            content_text?: string | null;
        };
        /** WorkspaceItemUpsertResponse */
        WorkspaceItemUpsertResponse: {
            item: components["schemas"]["SharedWorkspaceItemRead"];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    healthcheck_api_health_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
    start_github_oauth_api_auth_github_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            307: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    read_github_connection_api_auth_github_connection_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GitHubConnectionStatusResponse"];
                };
            };
        };
    };
    complete_github_oauth_api_auth_github_callback_get: {
        parameters: {
            query: {
                code: string;
                state: string;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            307: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    read_current_user_api_auth_me_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuthMeResponse"];
                };
            };
        };
    };
    get_jobs_api_jobs_get: {
        parameters: {
            query?: {
                agent_team_id?: string | null;
                agent_id?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutomationJobListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_job_api_jobs_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AutomationJobCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutomationJobResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    patch_job_api_jobs__job_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AutomationJobUpdateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutomationJobResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_run_job_api_jobs__job_id__run_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AutomationJobRunResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_github_repositories_api_github_repositories_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GitHubRepositoryListResponse"];
                };
            };
        };
    };
    export_workspace_item_api_github_teams__team_id__workspace_items__item_id__export_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                team_id: string;
                item_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["GitHubExportRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["GitHubExportResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_teams_api_teams_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamListResponse"];
                };
            };
        };
    };
    create_team_api_teams_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TeamCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamCreateResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_role_templates_api_role_templates_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RoleTemplateListResponse"];
                };
            };
        };
    };
    get_team_workspace_api_teams__team_id__workspace_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                team_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamWorkspaceResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_team_artifacts_api_teams__team_id__artifacts_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                team_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamArtifactListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_workspace_item_api_teams__team_id__workspace_items_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                team_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkspaceItemUpsertRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkspaceItemUpsertResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_team_conversations_api_teams__team_id__conversations_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                team_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamConversationListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_team_tasks_api_teams__team_id__tasks_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                team_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamTaskListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_run_team_inbox_cycle_api_teams__team_id__inbox_run_cycle_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                team_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamInboxCycleResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_team_huddle_api_teams__team_id__huddles_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                team_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TeamHuddleCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamHuddleCreateResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_team_member_response_api_teams__team_id__agents__agent_id__responses_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                team_id: string;
                agent_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TeamResponseCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentResponseCreateResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_team_response_api_teams__team_id__responses_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                team_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TeamResponseCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamResponseCreateResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_agents_api_agents_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentListResponse"];
                };
            };
        };
    };
    get_agent_conversations_api_agents__agent_id__conversations_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                agent_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ConversationListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_agent_inbox_api_agents__agent_id__inbox_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                agent_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamTaskListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_claim_next_inbox_task_api_agents__agent_id__inbox_claim_next_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                agent_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentInboxClaimResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_run_next_inbox_task_api_agents__agent_id__inbox_run_next_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                agent_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentInboxRunResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_agent_response_api_agents__agent_id__responses_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                agent_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AgentResponseCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AgentResponseCreateResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_task_updates_api_tasks__task_id__updates_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamTaskUpdateListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_task_delegate_api_tasks__task_id__delegate_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TeamTaskDelegateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamTaskMutationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_task_report_api_tasks__task_id__reports_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TeamTaskReportRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamTaskMutationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_task_message_api_tasks__task_id__messages_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TeamTaskMessageRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamTaskMutationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    post_task_complete_api_tasks__task_id__complete_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                task_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TeamTaskCompleteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TeamTaskMutationResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_conversation_messages_api_conversations__conversation_id__messages_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                conversation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MessageListResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    stream_conversation_events_api_conversations__conversation_id__stream_get: {
        parameters: {
            query?: {
                max_events?: number | null;
                poll_interval_seconds?: number;
                idle_timeout_seconds?: number;
            };
            header?: never;
            path: {
                conversation_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_secrets_api_secrets_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SecretListResponse"];
                };
            };
        };
    };
    create_secret_api_secrets_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SecretCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SecretCreateResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    remove_secret_api_secrets__secret_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                secret_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SecretDeleteResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_agent_runtime_api_agents__agent_id__runtime_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                agent_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuntimeLeaseResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    provision_agent_runtime_api_agents__agent_id__runtime_provision_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                agent_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuntimeLeaseResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    verify_agent_runtime_api_agents__agent_id__runtime_verify_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                agent_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuntimeLeaseResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    restart_agent_runtime_api_agents__agent_id__runtime_restart_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                agent_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RuntimeLeaseResponse"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_poller_status_api_system_poller_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PollerStatusResponse"];
                };
            };
        };
    };
    healthz_healthz_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": {
                        [key: string]: string;
                    };
                };
            };
        };
    };
}

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
  return `Request failed with ${result.response.status}`;
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
        request.headers.set("Authorization", `Bearer ${token}`);
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
      headers.set("Authorization", `Bearer ${token}`);
    }

    const done = (async () => {
      try {
        const response = await fetcher(
          `${options.baseUrl}/api/conversations/${conversationId}/stream`,
          {
            method: "GET",
            headers,
            signal: controller.signal,
          },
        );

        if (!response.ok) {
          throw new Error(`Request failed with ${response.status}`);
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
          const segments = buffer.split("\n\n");
          buffer = segments.pop() ?? "";

          for (const segment of segments) {
            const dataLine = segment
              .split("\n")
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
    healthcheck: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/health">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/health">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/health"));
      }
      return requestData((client.GET as any)("/api/health", init));
    },
    startGithubOauth: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/auth/github">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/auth/github">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/auth/github"));
      }
      return requestData((client.GET as any)("/api/auth/github", init));
    },
    readGithubConnection: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/auth/github/connection">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/auth/github/connection">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/auth/github/connection"));
      }
      return requestData((client.GET as any)("/api/auth/github/connection", init));
    },
    completeGithubOauth: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/auth/github/callback">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/auth/github/callback">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/auth/github/callback"));
      }
      return requestData((client.GET as any)("/api/auth/github/callback", init));
    },
    readCurrentUser: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/auth/me">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/auth/me">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/auth/me"));
      }
      return requestData((client.GET as any)("/api/auth/me", init));
    },
    getJobs: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/jobs">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/jobs">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/jobs"));
      }
      return requestData((client.GET as any)("/api/jobs", init));
    },
    postJob: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/jobs">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/jobs">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/jobs"));
      }
      return requestData((client.POST as any)("/api/jobs", init));
    },
    patchJob: (init?: any): Promise<[MethodResponse<Client<paths>, "patch", "/api/jobs/{job_id}">] extends [never] ? unknown : MethodResponse<Client<paths>, "patch", "/api/jobs/{job_id}">> => {
      if (init === undefined) {
        return requestData((client.PATCH as any)("/api/jobs/{job_id}"));
      }
      return requestData((client.PATCH as any)("/api/jobs/{job_id}", init));
    },
    postRunJob: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/jobs/{job_id}/run">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/jobs/{job_id}/run">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/jobs/{job_id}/run"));
      }
      return requestData((client.POST as any)("/api/jobs/{job_id}/run", init));
    },
    getGithubRepositories: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/github/repositories">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/github/repositories">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/github/repositories"));
      }
      return requestData((client.GET as any)("/api/github/repositories", init));
    },
    exportWorkspaceItem: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/github/teams/{team_id}/workspace/items/{item_id}/export">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/github/teams/{team_id}/workspace/items/{item_id}/export">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/github/teams/{team_id}/workspace/items/{item_id}/export"));
      }
      return requestData((client.POST as any)("/api/github/teams/{team_id}/workspace/items/{item_id}/export", init));
    },
    listTeams: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/teams">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/teams">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/teams"));
      }
      return requestData((client.GET as any)("/api/teams", init));
    },
    createTeam: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/teams">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/teams">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/teams"));
      }
      return requestData((client.POST as any)("/api/teams", init));
    },
    getRoleTemplates: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/role-templates">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/role-templates">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/role-templates"));
      }
      return requestData((client.GET as any)("/api/role-templates", init));
    },
    getTeamWorkspace: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/teams/{team_id}/workspace">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/teams/{team_id}/workspace">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/teams/{team_id}/workspace"));
      }
      return requestData((client.GET as any)("/api/teams/{team_id}/workspace", init));
    },
    getTeamArtifacts: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/teams/{team_id}/artifacts">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/teams/{team_id}/artifacts">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/teams/{team_id}/artifacts"));
      }
      return requestData((client.GET as any)("/api/teams/{team_id}/artifacts", init));
    },
    createWorkspaceItem: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/teams/{team_id}/workspace/items">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/teams/{team_id}/workspace/items">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/teams/{team_id}/workspace/items"));
      }
      return requestData((client.POST as any)("/api/teams/{team_id}/workspace/items", init));
    },
    getTeamConversations: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/teams/{team_id}/conversations">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/teams/{team_id}/conversations">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/teams/{team_id}/conversations"));
      }
      return requestData((client.GET as any)("/api/teams/{team_id}/conversations", init));
    },
    getTeamTasks: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/teams/{team_id}/tasks">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/teams/{team_id}/tasks">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/teams/{team_id}/tasks"));
      }
      return requestData((client.GET as any)("/api/teams/{team_id}/tasks", init));
    },
    postRunTeamInboxCycle: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/teams/{team_id}/inbox/run-cycle">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/teams/{team_id}/inbox/run-cycle">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/teams/{team_id}/inbox/run-cycle"));
      }
      return requestData((client.POST as any)("/api/teams/{team_id}/inbox/run-cycle", init));
    },
    createTeamHuddle: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/teams/{team_id}/huddles">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/teams/{team_id}/huddles">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/teams/{team_id}/huddles"));
      }
      return requestData((client.POST as any)("/api/teams/{team_id}/huddles", init));
    },
    createTeamMemberResponse: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/teams/{team_id}/agents/{agent_id}/responses">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/teams/{team_id}/agents/{agent_id}/responses">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/teams/{team_id}/agents/{agent_id}/responses"));
      }
      return requestData((client.POST as any)("/api/teams/{team_id}/agents/{agent_id}/responses", init));
    },
    createTeamResponse: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/teams/{team_id}/responses">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/teams/{team_id}/responses">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/teams/{team_id}/responses"));
      }
      return requestData((client.POST as any)("/api/teams/{team_id}/responses", init));
    },
    listAgents: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/agents">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/agents">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/agents"));
      }
      return requestData((client.GET as any)("/api/agents", init));
    },
    getAgentConversations: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/agents/{agent_id}/conversations">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/agents/{agent_id}/conversations">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/agents/{agent_id}/conversations"));
      }
      return requestData((client.GET as any)("/api/agents/{agent_id}/conversations", init));
    },
    getAgentInbox: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/agents/{agent_id}/inbox">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/agents/{agent_id}/inbox">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/agents/{agent_id}/inbox"));
      }
      return requestData((client.GET as any)("/api/agents/{agent_id}/inbox", init));
    },
    postClaimNextInboxTask: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/inbox/claim-next">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/inbox/claim-next">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/agents/{agent_id}/inbox/claim-next"));
      }
      return requestData((client.POST as any)("/api/agents/{agent_id}/inbox/claim-next", init));
    },
    postRunNextInboxTask: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/inbox/run-next">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/inbox/run-next">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/agents/{agent_id}/inbox/run-next"));
      }
      return requestData((client.POST as any)("/api/agents/{agent_id}/inbox/run-next", init));
    },
    createAgentResponse: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/responses">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/responses">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/agents/{agent_id}/responses"));
      }
      return requestData((client.POST as any)("/api/agents/{agent_id}/responses", init));
    },
    getTaskUpdates: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/tasks/{task_id}/updates">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/tasks/{task_id}/updates">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/tasks/{task_id}/updates"));
      }
      return requestData((client.GET as any)("/api/tasks/{task_id}/updates", init));
    },
    postTaskDelegate: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/tasks/{task_id}/delegate">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/tasks/{task_id}/delegate">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/tasks/{task_id}/delegate"));
      }
      return requestData((client.POST as any)("/api/tasks/{task_id}/delegate", init));
    },
    postTaskReport: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/tasks/{task_id}/reports">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/tasks/{task_id}/reports">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/tasks/{task_id}/reports"));
      }
      return requestData((client.POST as any)("/api/tasks/{task_id}/reports", init));
    },
    postTaskMessage: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/tasks/{task_id}/messages">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/tasks/{task_id}/messages">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/tasks/{task_id}/messages"));
      }
      return requestData((client.POST as any)("/api/tasks/{task_id}/messages", init));
    },
    postTaskComplete: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/tasks/{task_id}/complete">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/tasks/{task_id}/complete">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/tasks/{task_id}/complete"));
      }
      return requestData((client.POST as any)("/api/tasks/{task_id}/complete", init));
    },
    getConversationMessages: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/conversations/{conversation_id}/messages">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/conversations/{conversation_id}/messages">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/conversations/{conversation_id}/messages"));
      }
      return requestData((client.GET as any)("/api/conversations/{conversation_id}/messages", init));
    },
    listSecrets: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/secrets">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/secrets">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/secrets"));
      }
      return requestData((client.GET as any)("/api/secrets", init));
    },
    createSecret: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/secrets">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/secrets">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/secrets"));
      }
      return requestData((client.POST as any)("/api/secrets", init));
    },
    removeSecret: (init?: any): Promise<[MethodResponse<Client<paths>, "delete", "/api/secrets/{secret_id}">] extends [never] ? unknown : MethodResponse<Client<paths>, "delete", "/api/secrets/{secret_id}">> => {
      if (init === undefined) {
        return requestData((client.DELETE as any)("/api/secrets/{secret_id}"));
      }
      return requestData((client.DELETE as any)("/api/secrets/{secret_id}", init));
    },
    getAgentRuntime: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/agents/{agent_id}/runtime">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/agents/{agent_id}/runtime">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/agents/{agent_id}/runtime"));
      }
      return requestData((client.GET as any)("/api/agents/{agent_id}/runtime", init));
    },
    provisionAgentRuntime: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/runtime/provision">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/runtime/provision">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/agents/{agent_id}/runtime/provision"));
      }
      return requestData((client.POST as any)("/api/agents/{agent_id}/runtime/provision", init));
    },
    verifyAgentRuntime: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/runtime/verify">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/runtime/verify">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/agents/{agent_id}/runtime/verify"));
      }
      return requestData((client.POST as any)("/api/agents/{agent_id}/runtime/verify", init));
    },
    restartAgentRuntime: (init?: any): Promise<[MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/runtime/restart">] extends [never] ? unknown : MethodResponse<Client<paths>, "post", "/api/agents/{agent_id}/runtime/restart">> => {
      if (init === undefined) {
        return requestData((client.POST as any)("/api/agents/{agent_id}/runtime/restart"));
      }
      return requestData((client.POST as any)("/api/agents/{agent_id}/runtime/restart", init));
    },
    getPollerStatus: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/api/system/poller">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/api/system/poller">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/api/system/poller"));
      }
      return requestData((client.GET as any)("/api/system/poller", init));
    },
    healthzHealthzGet: (init?: any): Promise<[MethodResponse<Client<paths>, "get", "/healthz">] extends [never] ? unknown : MethodResponse<Client<paths>, "get", "/healthz">> => {
      if (init === undefined) {
        return requestData((client.GET as any)("/healthz"));
      }
      return requestData((client.GET as any)("/healthz", init));
    },
    streamConversationEvents,
  });
}

