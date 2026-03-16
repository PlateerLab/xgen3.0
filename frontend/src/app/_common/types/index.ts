// ============================================
// XGEN 3.0 Core Types
// ============================================

// --- Agent ---
export interface Agent {
  id: string;
  name: string;
  description: string;
  model: string;
  tools: string[];
  system_prompt: string;
  approval_required?: string[];
  created_at: string;
  updated_at: string;
  status: 'active' | 'inactive' | 'draft';
}

export interface AgentSummary {
  id: string;
  name: string;
  description: string;
  model: string;
  tool_count: number;
  status: 'active' | 'inactive' | 'draft';
  last_run?: string;
}

// --- Tool ---
export interface Tool {
  name: string;
  description: string;
  parameters: Record<string, ToolParameter>;
  source: 'builtin' | 'custom' | 'mcp' | 'graph';
}

export interface ToolParameter {
  type: string;
  description: string;
  required?: boolean;
  default?: unknown;
}

// --- Message ---
export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  tool_calls?: ToolCall[];
  tool_result?: ToolResult;
  think?: string;
  approval?: ApprovalRequest;
  is_streaming?: boolean;
}

export interface ToolCall {
  id: string;
  tool: string;
  params: Record<string, unknown>;
}

export interface ToolResult {
  tool_call_id: string;
  tool: string;
  result: unknown;
  duration_ms: number;
  success: boolean;
  error?: string;
}

export interface ApprovalRequest {
  action: string;
  reason: string;
  status: 'pending' | 'approved' | 'denied';
}

// --- Session ---
export interface Session {
  id: string;
  agent_id: string;
  agent_name: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  last_message?: string;
}

// --- Trace ---
export interface Trace {
  trace_id: string;
  session_id: string;
  agent: string;
  timestamp: string;
  total_duration_ms: number;
  steps: TraceStep[];
}

export interface TraceStep {
  type: 'think' | 'tool_call' | 'response' | 'approval' | 'error';
  timestamp: string;
  duration_ms: number;
  // think
  model?: string;
  input_tokens?: number;
  output_tokens?: number;
  // tool_call
  tool?: string;
  params?: Record<string, unknown>;
  result?: unknown;
  success?: boolean;
  error?: string;
  // response
  text?: string;
}

// --- SSE ---
export type SSEEventType =
  | 'message_start'
  | 'content_delta'
  | 'content_done'
  | 'tool_call_start'
  | 'tool_call_done'
  | 'think_start'
  | 'think_delta'
  | 'think_done'
  | 'approval_required'
  | 'error'
  | 'done';

export interface SSEEvent {
  event: SSEEventType;
  data: Record<string, unknown>;
}

// --- API Responses ---
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
