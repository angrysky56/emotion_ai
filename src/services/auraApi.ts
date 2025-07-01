/**
 * Enhanced Aura API Service
 * Improved error handling, retry logic, and backend integration
 */

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

export interface ConversationRequest {
  user_id: string;
  message: string;
  session_id?: string;
}

export interface EmotionalState {
  name: string;
  intensity: string;
  brainwave: string;
  neurotransmitter: string;
  description?: string;
}

export interface CognitiveState {
  focus: string;
  description: string;
}

export interface ConversationResponse {
  response: string;
  emotional_state: EmotionalState;
  cognitive_state: CognitiveState;
  session_id: string;
  thinking_content?: string;
  thinking_metrics?: {
    total_chunks: number;
    thinking_chunks: number;
    answer_chunks: number;
    processing_time_ms: number;
  };
  has_thinking: boolean;
}

export interface SearchRequest {
  user_id: string;
  query: string;
  n_results?: number;
}

export interface SearchResult {
  content: string;
  metadata: any;
  similarity: number;
}

export interface SearchResponse {
  results: SearchResult[];
  query: string;
  total_found: number;
  search_type: string;
  includes_video_archives?: boolean;
}

export interface ChatSession {
  session_id: string;
  last_message: string;
  message_count: number;
  timestamp: string;
}

export interface ChatHistoryResponse {
  sessions: ChatSession[];
  total_sessions: number;
  user_id: string;
}

export interface ChatMessage {
  id: string;
  content: string;
  sender: 'user' | 'aura';
  timestamp: string;
  emotional_state?: EmotionalState;
  cognitive_state?: CognitiveState;
}

export interface EmotionalAnalysisResponse {
  period_days: number;
  period_type?: string;
  custom_days?: number;
  total_entries: number;
  dominant_emotions: Array<[string, number]>;
  intensity_distribution: Record<string, number>;
  brainwave_patterns?: Record<string, number>;
  emotional_stability: number;
  recommendations: string[];
}

export interface HealthCheckResponse {
  status: string;
  timestamp: string;
  vector_db: string;
  aura_file_system: string;
  error?: string;
}

// ============================================================================
// ENHANCED AURA API CLASS
// ============================================================================

/**
 * Singleton class to interact with the Aura backend API.
 * Handles HTTP requests, retries, health checks, and error logging.
 */
export class AuraAPI {
  private static instance: AuraAPI;
  private readonly baseUrl: string;
  private readonly timeout: number;
  private readonly maxRetries: number;
  private requestId: number = 0;

  // Connection state tracking
  private isConnected: boolean = false;
  private lastHealthCheck: number = 0;
  private healthCheckInterval: number = 300000; // 300 seconds

  /**
   * Initializes the AuraAPI instance, sets base URL, timeouts, retries, and starts health monitoring.
   * @private
   */
  private constructor() {
    this.baseUrl = this.getApiBaseUrl();
    this.timeout = 300000; // 300 seconds
    this.maxRetries = 3;

    // Start periodic health checks
    this.startHealthMonitoring();
  }

  /**
   * Retrieves the single AuraAPI instance (singleton).
   * @returns {AuraAPI} The AuraAPI instance.
   */
  static getInstance(): AuraAPI {
    if (!AuraAPI.instance) {
      AuraAPI.instance = new AuraAPI();
    }
    return AuraAPI.instance;
  }

  // ============================================================================
  // CONNECTION MANAGEMENT
  // ============================================================================

  private getApiBaseUrl(): string {
    // Try to detect the correct API URL
    const hostname = window.location.hostname;

    if (hostname === 'localhost' || hostname === '127.0.0.1') {
      return 'http://localhost:8000';
    }

    // For production, use same host with different port or path
    return `${window.location.protocol}//${hostname}:8000`;
  }

  /**
   * Starts periodic health monitoring by performing initial and interval health checks.
   * @private
   * @returns {Promise<void>}
   */
  private async startHealthMonitoring(): Promise<void> {
    // Initial health check
    await this.performHealthCheck();

    // Set up periodic health checks
    setInterval(() => {
      this.performHealthCheck().catch(error => {
        console.warn('🔴 Periodic health check failed:', error);
      });
    }, this.healthCheckInterval);
  }

  /**
   * Performs a health check against the /health endpoint.
   * Updates isConnected and lastHealthCheck.
   * @private
   * @returns {Promise<void>}
   */
  private async performHealthCheck(): Promise<void> {
    try {
      const response = await this.makeRequest<HealthCheckResponse>('/health', {
        method: 'GET',
        skipRetry: true,
        skipLogging: true,
        skipCustomHeaders: true // Pass the new option for health checks
      });

      this.isConnected = response.status === 'operational';
      this.lastHealthCheck = Date.now();

      if (!this.isConnected) {
        console.warn(`🔴 Backend health check indicates unhealthy state. Expected status "operational" but received:`, response);
      } else {
        console.log('🟢 Backend health check successful:', response);
      }
    } catch (error) {
      this.isConnected = false;
      this.lastHealthCheck = Date.now();
      console.warn('🔴 Backend health check failed:', error);
    }
  }

  /**
   * Returns current connection status and timestamp of last health check.
   * @returns {{ isConnected: boolean; lastCheck: number }}
   */
  public getConnectionStatus(): { isConnected: boolean; lastCheck: number } {
    return {
      isConnected: this.isConnected,
      lastCheck: this.lastHealthCheck
    };
  }

  // ============================================================================
  // CORE HTTP CLIENT WITH ENHANCED ERROR HANDLING
  // ============================================================================
  /**
   * Generates a unique request identifier.
   * @private
   * @returns {string}
   */
  private generateRequestId(): string {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return `req_${crypto.randomUUID()}`;
    }
    return `req_${++this.requestId}_${Date.now()}`;
  }

  /**
   * Core HTTP client with retry logic, timeouts, logging, and custom headers.
   * @private
   * @template T
   * @param {string} endpoint API endpoint path.
   * @param {{ method: 'GET' | 'POST' | 'DELETE'; body?: any; skipRetry?: boolean; skipLogging?: boolean; timeout?: number; skipCustomHeaders?: boolean; }} options Request options.
   * @returns {Promise<T>} Parsed JSON response or text.
   * @throws Will throw an error if all retry attempts fail.
   */
  private async makeRequest<T>(
    endpoint: string,
    options: {
      method: 'GET' | 'POST' | 'DELETE';
      body?: any;
      skipRetry?: boolean;
      skipLogging?: boolean;
      timeout?: number;
      skipCustomHeaders?: boolean;
    }
  ): Promise<T> {
    const requestId = this.generateRequestId();
    const url = `${this.baseUrl}${endpoint}`;
    const requestTimeout = options.timeout || this.timeout;

    if (!options.skipLogging) {
      console.log(`🌐 [${requestId}] ${options.method} ${endpoint}`);
    }
    let lastError: Error | null = null;
    const maxAttempts = options.skipRetry ? 1 : this.maxRetries;

    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
      const headers: Record<string, string> = {}; // Initialize empty headers

      if (!options.skipCustomHeaders) { // Conditionally add custom headers
        headers['X-Request-ID'] = requestId;
        headers['X-Attempt'] = attempt.toString();
      }

      if (options.body) {
        headers['Content-Type'] = 'application/json';
      }

      try {
        const controller = new AbortController();
        let timeoutId: any; // Declare timeoutId here

        // Set timeout for the request
        timeoutId = setTimeout(() => controller.abort(), requestTimeout);

        // Only include 'body' for non-GET requests
        const fetchOptions: RequestInit = {
          method: options.method,
          headers: headers,
          signal: controller.signal,
        };
        if (options.method !== 'GET' && options.body) {
          fetchOptions.body = JSON.stringify(options.body);
        }

        const response = await fetch(url, fetchOptions);
        clearTimeout(timeoutId); // Clear timeout if request completes

        if (!response.ok) {
          const errorText = await response.text().catch(() => 'Unknown error');
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        // Check if response is JSON before parsing
        const contentType = response.headers.get('Content-Type') || '';
        let result: any;
        if (contentType.includes('application/json')) {
          result = await response.json();
        } else {
          result = await response.text();
          if (!options.skipLogging) {
            console.warn(`⚠️ [${requestId}] Response is not JSON. Content-Type: ${contentType}`);
          }
        }
        return result;

      } catch (error) {
        lastError = error as Error;

        if (!options.skipLogging) {
          console.warn(`⚠️ [${requestId}] Attempt ${attempt}/${maxAttempts} failed:`, error);
        }

        // Don't retry on certain errors
        if (this.isNonRetryableError(error as Error) || attempt === maxAttempts) {
          break;
        }

        // Exponential backoff with jitter
        const baseDelay = Math.min(1000 * Math.pow(2, attempt - 1), 5000);
        const jitter = Math.random() * 0.3 * baseDelay;
        const delay = baseDelay + jitter;

        if (!options.skipLogging) {
          console.log(`⏳ [${requestId}] Retrying in ${Math.round(delay)}ms...`);
        }

        await this.sleep(delay);
      }
    }

    if (!options.skipLogging) {
      console.error(`❌ [${requestId}] All attempts failed`);
    }

    throw lastError || new Error('Request failed after all retry attempts');
  }

  /**
   * Determines if an error is non-retryable.
   * @private
   * @param {Error} error The error instance to evaluate.
   * @returns {boolean} True if error should not be retried.
   */
  private isNonRetryableError(error: Error): boolean {
    const message = error.message.toLowerCase();

    // Don't retry these types of errors
    const nonRetryablePatterns = [
      'http 400', // Bad Request
      'http 401', // Unauthorized
      'http 403', // Forbidden
      'http 404', // Not Found
      'http 422', // Unprocessable Entity
      'json', // JSON parsing errors
      'syntax'
    ];

    return nonRetryablePatterns.some(pattern => message.includes(pattern));
  }

  /**
   * Delays execution for a specified duration.
   * @private
   * @param {number} ms Milliseconds to sleep.
   * @returns {Promise<void>}
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ============================================================================
  // CORE API METHODS
  // ============================================================================

  /**
   * Checks backend health. External facing method wrapping internal request.
   * @returns {Promise<HealthCheckResponse>}
   */
  async healthCheck(): Promise<HealthCheckResponse> {
    return this.makeRequest<HealthCheckResponse>('/health', {
      method: 'GET',
      timeout: 50000 // Shorter timeout for health checks
    });
  }

  /**
   * Sends a message to the conversation endpoint.
   * @param {ConversationRequest} request The conversation payload.
   * @returns {Promise<ConversationResponse>}
   * @throws Will throw error if validation or request fails.
   */
  async sendMessage(request: ConversationRequest): Promise<ConversationResponse> {
    if (!request.user_id || !request.message.trim()) {
      throw new Error('User ID and message are required');
    }

    try {
      const response = await this.makeRequest<ConversationResponse>('/conversation', {
        method: 'POST',
        body: request,
        timeout: 600000 // Longer timeout for conversation processing
      });

      // Validate response structure
      if (!response.response || !response.emotional_state || !response.cognitive_state) {
        throw new Error('Invalid response structure from backend');
      }

      return response;
    } catch (error) {
      console.error('❌ Conversation error:', error);
      throw new Error(`Failed to send message: ${(error as Error).message}`);
    }
  }

  /**
   * Searches user memories based on a query.
   * @param {string} userId The user identifier.
   * @param {string} query Search query string.
   * @param {number} [nResults=50000] Number of results to return (1-50000).
   * @returns {Promise<SearchResponse>}
   */
  async searchMemories(userId: string, query: string, nResults: number = 50000): Promise<SearchResponse> {
    if (!userId || !query.trim()) {
      throw new Error('User ID and query are required');
    }

    try {
      const response = await this.makeRequest<SearchResponse>('/search', {
        method: 'POST',
        body: {
          user_id: userId,
          query: query.trim(),
          n_results: Math.max(1, Math.min(nResults, 50000)) // Clamp between 1 and 50000
        }
      });

      // Ensure results array exists
      if (!response.results) {
        response.results = [];
      }

      return response;
    } catch (error) {
      console.error('❌ Memory search error:', error);
      throw new Error(`Failed to search memories: ${(error as Error).message}`);
    }
  }

  /**
   * Retrieves emotional analysis for a user over a given period.
   * @param {string} userId The user identifier.
   * @param {string} [period='week'] The analysis period (e.g., 'day', 'week', 'month').
   * @param {number} [customDays] Custom number of days for analysis.
   * @returns {Promise<EmotionalAnalysisResponse>}
   */
  async getEmotionalAnalysis(
    userId: string,
    period: string = 'week',
    customDays?: number
  ): Promise<EmotionalAnalysisResponse> {
    if (!userId) {
      throw new Error('User ID is required');
    }

    try {
      let url = `/emotional-analysis/${encodeURIComponent(userId)}?period=${encodeURIComponent(period)}`;
      if (customDays !== undefined) {
        url += `&custom_days=${customDays}`;
      }

      const response = await this.makeRequest<EmotionalAnalysisResponse>(url, {
        method: 'GET'
      });

      // Ensure required fields exist
      if (!response.dominant_emotions) {
        response.dominant_emotions = [];
      }
      if (!response.recommendations) {
        response.recommendations = [];
      }

      return response;
    } catch (error) {
      console.error('❌ Emotional analysis error:', error);
      throw new Error(`Failed to get emotional analysis: ${(error as Error).message}`);
    }
  }

  /**
   * Retrieves chat history sessions for a user.
   * @param {string} userId The user identifier.
   * @param {number} [limit=50000] Maximum sessions to retrieve (1-50000).
   * @returns {Promise<ChatHistoryResponse>}
   */
  async getChatHistory(userId: string, limit: number = 50000): Promise<ChatHistoryResponse> {
    if (!userId) {
      throw new Error('User ID is required');
    }

    try {
      const clampedLimit = Math.max(1, Math.min(limit, 200000)); // Clamp between 1 and 200000
      const response = await this.makeRequest<ChatHistoryResponse>(
        `/chat-history/${encodeURIComponent(userId)}?limit=${clampedLimit}`,
        { method: 'GET' }
      );

      // Ensure sessions array exists
      if (!response.sessions) {
        response.sessions = [];
      }

      return response;
    } catch (error) {
      console.error('❌ Chat history error:', error);
      throw new Error(`Failed to get chat history: ${(error as Error).message}`);
    }
  }

  /**
   * Retrieves messages for a specific user session.
   * @param {string} userId The user identifier.
   * @param {string} sessionId The session identifier.
   * @returns {Promise<ChatMessage[]>}
   */
  async getSessionMessages(userId: string, sessionId: string): Promise<ChatMessage[]> {
    if (!userId || !sessionId) {
      throw new Error('User ID and session ID are required');
    }

    try {
      const response = await this.makeRequest<ChatMessage[]>(
        `/chat-history/${encodeURIComponent(userId)}/${encodeURIComponent(sessionId)}`,
        { method: 'GET' }
      );

      return Array.isArray(response) ? response : [];
    } catch (error) {
      console.error('❌ Session messages error:', error);
      throw new Error(`Failed to get session messages: ${(error as Error).message}`);
    }
  }

  /**
   * Deletes a specific chat session for a user.
   * @param {string} userId The user identifier.
   * @param {string} sessionId The session identifier.
   * @returns {Promise<{ message: string; deleted_count: number }>}
   */
  async deleteChatSession(userId: string, sessionId: string): Promise<{ message: string; deleted_count: number }> {
    if (!userId || !sessionId) {
      throw new Error('User ID and session ID are required');
    }

    try {
      return await this.makeRequest<{ message: string; deleted_count: number }>(
        `/chat-history/${encodeURIComponent(userId)}/${encodeURIComponent(sessionId)}`,
        { method: 'DELETE' }
      );
    } catch (error) {
      console.error('❌ Delete session error:', error);
      throw new Error(`Failed to delete session: ${(error as Error).message}`);
    }
  }

  /**
   * Clears all chat sessions for a user.
   * @param {string} userId The user identifier.
   * @returns {Promise<{ message: string; sessions_cleared: number }>}
   */
  async clearUserSessions(userId: string): Promise<{ message: string; sessions_cleared: number }> {
    if (!userId) {
      throw new Error('User ID is required');
    }

    try {
      return await this.makeRequest<{ message: string; sessions_cleared: number }>(
        `/sessions/${encodeURIComponent(userId)}`,
        { method: 'DELETE' }
      );
    } catch (error) {
      console.error('❌ Clear sessions error:', error);
      throw new Error(`Failed to clear sessions: ${(error as Error).message}`);
    }
  }

  /**
   * Exports user data in the specified format.
   * @param {string} userId The user identifier.
   * @param {string} [format='json'] Export format ('json', 'csv', 'html').
   * @returns {Promise<{ export_path: string; message: string }>}
   */
  async exportUserData(userId: string, format: string = 'json'): Promise<{ export_path: string; message: string }> {
    if (!userId) {
      throw new Error('User ID is required');
    }

    const validFormats = ['json', 'csv', 'html'];
    if (!validFormats.includes(format)) {
      throw new Error(`Invalid format. Must be one of: ${validFormats.join(', ')}`);
    }

    try {
      return await this.makeRequest<{ export_path: string; message: string }>(
        `/export/${encodeURIComponent(userId)}`,
        {
          method: 'POST',
          body: { format }
        }
      );
    } catch (error) {
      console.error('❌ Export user data error:', error);
      throw new Error(`Failed to export user data: ${(error as Error).message}`);
    }
  }

  /**
   * Executes a CLI command via the backend PTY session.
   * @param {string} projectPath The path to the project context for the command.
   * @param {string} command The command to execute.
   * @param {Record<string, string>} [envVars] Optional environment variables.
   * @returns {Promise<{ success: boolean; sessionId: string }>}
   */
  async executeCliCommand(
    projectPath: string,
    command: string,
    envVars?: Record<string, string>
  ): Promise<{ success: boolean; sessionId: string }> {
    if (!projectPath || !command) {
      throw new Error('Project path and command are required for CLI execution.');
    }

    try {
      const response = await this.makeRequest<{ success: boolean; sessionId: string }>('/api/cli/execute', {
        method: 'POST',
        body: {
          projectPath,
          command,
          envVars: envVars || {},
        },
      });
      if (!response.success || !response.sessionId) {
        throw new Error('Failed to execute CLI command or invalid response from server.');
      }
      return response;
    } catch (error) {
      console.error('❌ CLI execution error:', error);
      throw new Error(`Failed to execute CLI command: ${(error as Error).message}`);
    }
  }
}

// ============================================================================
// SINGLETON EXPORT
// ============================================================================

export const auraAPI = AuraAPI.getInstance();
export default auraAPI;
