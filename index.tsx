/**
 * Aura Frontend UI Manager
 */

import { marked } from 'marked';
import { AuraAPI, ConversationResponse, EmotionalState, CognitiveState } from './src/services/auraApi';

// ============================================================================
// CONFIGURATION & TYPES
// ============================================================================

interface ChatSession {
  session_id: string;
  last_message: string;
  message_count: number;
  timestamp: string;
}

// ============================================================================
// GLOBAL STATE MANAGEMENT
// ============================================================================

class AuraUIManager {
  private api: AuraAPI;
  private currentSessionId: string | null = null;
  private userName: string | null = null;
  private backendConnected = false;
  private typingIndicatorElement: HTMLElement | null = null;
  private chatSessions: ChatSession[] = [];

  // DOM Elements
  private messageArea!: HTMLElement;
  private messageInput!: HTMLInputElement;
  private chatForm!: HTMLFormElement;
  private sendButton!: HTMLButtonElement;
  private emotionStatusElement!: HTMLElement;
  private emotionDetailsElement!: HTMLElement;
  private cognitiveFocusElement!: HTMLElement;
  private cognitiveFocusDetailsElement!: HTMLElement;
  private chatHistoryList!: HTMLElement;
  private leftPanel!: HTMLElement;
  private rightPanel!: HTMLElement;

  // Enhanced header elements
  private headerElement!: HTMLElement;
  private userGreetingElement!: HTMLElement;
  private brainwaveValueElement!: HTMLElement;
  private ntValueElement!: HTMLElement;
  private emotionIconElement!: HTMLElement;
  private emotionIntensityElement!: HTMLElement;
  private cognitiveIconElement!: HTMLElement;
  private cognitiveEnergyElement!: HTMLElement;
  private systemStatusElement!: HTMLElement;
  private connectionStatusElement!: HTMLElement;
  private systemDetailsElement!: HTMLElement;
  private wavePatternElement!: HTMLElement;
  private chemicalLevelElement!: HTMLElement;

  // Simplified user management elements
  private inlineUsernameInput!: HTMLInputElement;
  private inlineSaveButton!: HTMLButtonElement;
  private userStatus!: HTMLElement;

  constructor(apiInstance?: AuraAPI) {
    this.api = apiInstance ?? AuraAPI.getInstance();
  }

  public async initialize(): Promise<void> {
    console.log("🚀 Initializing Aura UI Manager...");
    await this.initializeDOM();
    await this.checkBackendHealth();
    await this.loadUserData();
    this.setupUI();
    this.initializeEventListeners();
    await this.startChat();

    // Set up periodic chat history refresh (every 30 seconds)
    setInterval(() => {
      if (this.userName && this.backendConnected) {
        this.loadChatHistory().catch(error => {
          console.warn("⚠️ Periodic chat history refresh failed:", error);
        });
      }
    }, 30000);

    console.log("✅ Aura UI Manager initialized successfully.");
  }

  // ============================================================================
  // INITIALIZATION
  // ============================================================================

  private async initializeDOM(): Promise<void> {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      await new Promise(resolve => document.addEventListener('DOMContentLoaded', resolve));
    }

    // Get essential DOM elements
    this.messageArea = this.getRequiredElement('message-area');
    this.messageInput = this.getRequiredElement('message-input') as HTMLInputElement;
    this.chatForm = this.getRequiredElement('chat-form') as HTMLFormElement;
    this.sendButton = this.getRequiredElement('send-button') as HTMLButtonElement;
    this.emotionStatusElement = this.getRequiredElement('aura-emotion-status');
    this.emotionDetailsElement = this.getRequiredElement('aura-emotion-details');
    this.cognitiveFocusElement = this.getRequiredElement('aura-cognitive-focus');
    this.cognitiveFocusDetailsElement = this.getRequiredElement('aura-cognitive-focus-details');
    this.chatHistoryList = this.getRequiredElement('chat-history-list');
    this.leftPanel = this.getRequiredElement('left-panel');
    this.rightPanel = this.getRequiredElement('right-panel');

    // Enhanced header elements
    this.headerElement = this.getRequiredElement('aura-header');
    this.userGreetingElement = this.getRequiredElement('user-greeting');
    this.brainwaveValueElement = this.getRequiredElement('brainwave-value');
    this.ntValueElement = this.getRequiredElement('nt-value');
    this.emotionIconElement = this.getRequiredElement('emotion-icon');
    this.emotionIntensityElement = this.getRequiredElement('emotion-intensity');
    this.cognitiveIconElement = this.getRequiredElement('cognitive-icon');
    this.cognitiveEnergyElement = this.getRequiredElement('cognitive-energy');
    this.systemStatusElement = this.getRequiredElement('system-status');
    this.connectionStatusElement = this.getRequiredElement('connection-status');
    this.systemDetailsElement = this.getRequiredElement('system-details');
    this.wavePatternElement = this.getRequiredElement('wave-pattern');
    this.chemicalLevelElement = this.getRequiredElement('chemical-level');

    // Note: Simplified user management elements will be created dynamically in setupUsernameManagement()

    console.log("✅ Enhanced DOM elements initialized");
  }

  private getRequiredElement(id: string): HTMLElement {
    const element = document.getElementById(id);
    if (!element) {
      throw new Error(`Required element not found: ${id}`);
    }
    return element;
  }

  private async checkBackendHealth(): Promise<void> {
    try {
      console.log("🔍 Checking backend health...");
      this.updateSystemHealth('connecting', 'Checking...', 'Testing backend connection');

      const healthData = await this.api.healthCheck();
      this.backendConnected = true;
      this.updateSystemHealth('optimal', 'Connected', 'All systems operational');
      console.log("✅ Backend connected:", healthData);

      // Test if the backend is actually responding to conversation endpoint
      try {
        console.log("🧪 Testing backend endpoints...");
        // We'll test this during the first actual message
      } catch (testError) {
        console.warn("⚠️ Backend health check passed but endpoints may not be working:", testError);
        this.updateSystemHealth('warning', 'Limited', 'Some endpoints may not be responding');
      }

    } catch (error) {
      console.warn("⚠️ Backend health check failed:", error);
      this.backendConnected = false;
      this.updateSystemHealth('error', 'Disconnected', 'Backend connection failed');
      this.showConnectionWarning();
    }
  }

  private async loadUserData(): Promise<void> {
    try {
      const storedName = localStorage.getItem('auraUserName');

      if (this.isValidUsername(storedName)) {
        this.userName = storedName!.trim();
        console.log(`✅ User data loaded: ${this.userName}`);

        // Update all UI elements
        this.updateAllUsernameDisplays();
      } else {
        this.userName = null;
        console.log("📝 No valid user data found");

        // Clear invalid stored name
        if (storedName) {
          localStorage.removeItem('auraUserName');
          console.warn(`⚠️ Removed invalid stored username: "${storedName}"`);
        }

        this.updateAllUsernameDisplays();
      }
    } catch (error) {
      console.error("❌ Error loading user data:", error);
      this.userName = null;
      this.updateAllUsernameDisplays();
    }
  }

  // ============================================================================
  // UI SETUP
  // ============================================================================

  private setupUI(): void {
    this.setupTheme();
    this.setupMobileMenu();
    this.setupMemorySearch();
    this.setupEmotionalInsights();
    this.setupChatHistory();
    this.setupKeyboardShortcuts();
    this.setupEnhancedHeader();
    this.setupUsernameManagement();
    this.updateVideoArchiveStatus();
  }

  private setupTheme(): void {
    const themeToggle = document.getElementById('theme-toggle');
    const savedTheme = localStorage.getItem('aura_theme') || 'dark';

    document.documentElement.setAttribute('data-theme', savedTheme);

    themeToggle?.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('aura_theme', newTheme);
    });
  }

  private setupMobileMenu(): void {
    const leftMenuBtn = document.getElementById('left-menu-btn');
    const rightMenuBtn = document.getElementById('right-menu-btn');

    leftMenuBtn?.addEventListener('click', () => {
      this.leftPanel.classList.toggle('collapsed');
    });

    rightMenuBtn?.addEventListener('click', () => {
      this.rightPanel.classList.toggle('collapsed');
    });

    // Close panels when clicking outside on mobile
    document.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      if (window.innerWidth <= 1024) {
        if (!this.leftPanel.contains(target) && !leftMenuBtn?.contains(target)) {
          this.leftPanel.classList.add('collapsed');
        }
        if (!this.rightPanel.contains(target) && !rightMenuBtn?.contains(target)) {
          this.rightPanel.classList.add('collapsed');
        }
      }
    });
  }

  private setupChatHistory(): void {
    const newChatBtn = document.getElementById('new-chat-btn');
    newChatBtn?.addEventListener('click', () => this.createNewChat());

    // Load chat history after a small delay to ensure backend is ready
    setTimeout(() => {
      this.loadChatHistory();
    }, 500);
  }

  private setupMemorySearch(): void {
    const searchInput = document.getElementById('unified-search-input') as HTMLInputElement | null;
    const searchButton = document.getElementById('unified-search-button') as HTMLButtonElement | null;
    const searchResultsArea = document.getElementById('unified-search-results');
    const searchErrorElement = document.getElementById('unified-search-error'); // Element from your screenshot

    if (!searchInput || !searchButton || !searchResultsArea || !searchErrorElement) {
      console.error('Memory search UI elements not found. Search functionality will be disabled.');
      if (searchErrorElement) searchErrorElement.textContent = 'Search UI failed to load.';
      return;
    }

    // Initially disable search button if user is not known
    searchButton.disabled = !this.userName;

    searchButton.addEventListener('click', () => {
      const query = searchInput.value.trim();
      searchErrorElement.textContent = ''; // Clear previous errors
      searchResultsArea.innerHTML = '';   // Clear previous results

      if (!this.userName) {
        searchErrorElement.textContent = 'Error: User not identified. Please tell Aura your name in the chat.';
        console.warn('Memory search attempted without user identification.');
        return;
      }

      if (!query) {
        searchErrorElement.textContent = 'Please enter a search query.';
        return;
      }

      searchResultsArea.innerHTML = '<p>Searching memories...</p>';

      (async () => {
        try {
          console.log(`Searching memories for user "${this.userName}" with query "${query}"`);
          const response = await this.api.searchMemories(this.userName!, query);

          this.displaySearchResults(response, searchResultsArea);
        } catch (error: any) {
          console.error('Error during memory search:', error);
          searchErrorElement.textContent = `Search failed: ${error.message || 'Unknown error'}`;
          searchResultsArea.innerHTML = '<p>An error occurred during the search.</p>';
        }
      })();
    });
    console.log("✅ Unified Memory Search UI setup complete.");
  }

  private setupEmotionalInsights(): void {
    const showInsightsBtn = document.getElementById('show-insights');
    const insightsPeriod = document.getElementById('insights-period') as HTMLSelectElement;
    const insightsContent = document.getElementById('insights-content');

    if (!showInsightsBtn || !insightsPeriod || !insightsContent) return;

    showInsightsBtn.addEventListener('click', async () => {
      console.log(`📊 Emotional insights requested:`, { userName: this.userName, backendConnected: this.backendConnected });

      if (!this.userName || !this.backendConnected) {
        const errorMsg = !this.userName ? 'User not identified' : 'Backend not connected';
        insightsContent.innerHTML = `<div class="insights-data error">Error: ${errorMsg}</div>`;
        console.warn('⚠️ Emotional insights failed:', { userName: this.userName, backendConnected: this.backendConnected });
        return;
      }

      try {
        showInsightsBtn.textContent = 'Analyzing...';
        (showInsightsBtn as HTMLButtonElement).disabled = true;
        insightsContent.innerHTML = '<div class="insights-data">Analyzing emotional patterns...</div>';

        const period = insightsPeriod.value;
        console.log(`📤 Requesting emotional analysis for user: ${this.userName}, period: ${period}`);

        const analysis = await this.api.getEmotionalAnalysis(this.userName, period);
        console.log(`📥 Emotional analysis response:`, analysis);

        this.displayEmotionalInsights(analysis, insightsContent);

      } catch (error) {
        console.error('❌ Insights error:', error);
        insightsContent.innerHTML = `<div class="insights-data error">Failed to load insights: ${(error as Error).message}</div>`;
      } finally {
        showInsightsBtn.textContent = 'View Analysis';
        (showInsightsBtn as HTMLButtonElement).disabled = false;
      }
    });
  }

  private setupKeyboardShortcuts(): void {
    document.addEventListener('keydown', (e) => {
      // Ctrl/Cmd + Enter to send message
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        this.chatForm.dispatchEvent(new Event('submit'));
      }

      // Escape to close mobile panels
      if (e.key === 'Escape') {
        this.leftPanel.classList.add('collapsed');
        this.rightPanel.classList.add('collapsed');
      }
    });

    // Fixed message input handling - properly trigger form submission
    this.messageInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        // Trigger form submission event instead of calling handler directly
        this.chatForm.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      }
    });
  }

  private setupEnhancedHeader(): void {
    // Initialize header with default state
    this.updateSystemHealth('optimal', 'Connected', 'All systems operational');
    this.updateBrainwaveDisplay('Alpha', 'Default');
    this.updateNeurotransmitterDisplay('Serotonin', 70);

    // Set initial greeting
    this.updateUserGreeting();

    console.log("✅ Enhanced header initialized");
  }

  private setupUsernameManagement(): void {
    // Create the simplified user interface
    this.createSimplifiedUserInterface();

    // Load and display existing username
    this.loadAndDisplayStoredUsername();

    // Set up event listeners for simplified interface
    this.setupSimplifiedEventListeners();

    console.log("✅ Simplified username management setup complete");
  }

  private createSimplifiedUserInterface(): void {
    // Find the user controls container
    const userControlsContainer = document.getElementById('user-controls') ||
                                 document.querySelector('.user-controls');

    if (!userControlsContainer) {
      console.error("❌ User controls container not found");
      return;
    }

    // Replace dropdown with simplified inline interface
    userControlsContainer.innerHTML = `
      <div class="simplified-user-section">
        <span class="user-label">I'm</span>
        <input
          type="text"
          class="inline-username-input"
          id="inline-username-input"
          placeholder="Enter your name"
          maxlength="30"
          autocomplete="off"
          spellcheck="false"
        >
        <button class="inline-save-btn" id="inline-save-btn" disabled>Save</button>
        <div class="user-status hidden" id="user-status"></div>
      </div>
    `;

    // Store references to new elements
    this.inlineUsernameInput = document.getElementById('inline-username-input') as HTMLInputElement;
    this.inlineSaveButton = document.getElementById('inline-save-btn') as HTMLButtonElement;
    this.userStatus = document.getElementById('user-status') as HTMLElement;

    console.log("✅ Simplified user interface created");
  }

  private loadAndDisplayStoredUsername(): void {
    // This method is called after the simplified UI elements are created
    // Username is already loaded by loadUserData() in initialization
    // Just update the display elements
    this.updateAllUsernameDisplays();
    console.log("✅ Stored username displayed in simplified interface.");
  }

  private setupSimplifiedEventListeners(): void {
    if (!this.inlineUsernameInput || !this.inlineSaveButton) {
      console.error("❌ Simplified UI elements not found");
      return;
    }

    // Input validation with real-time feedback
    this.inlineUsernameInput.addEventListener('input', () => {
      this.handleUsernameInput();
    });

    // Save on Enter key
    this.inlineUsernameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        this.handleUsernameSave();
      }
    });

    // Save button click
    this.inlineSaveButton.addEventListener('click', () => {
      this.handleUsernameSave();
    });

    // Focus handling
    this.inlineUsernameInput.addEventListener('focus', () => {
      this.hideUserStatus();
    });

    console.log("✅ Simplified event listeners setup");
  }

  private handleUsernameInput(): void {
    const currentInput = this.inlineUsernameInput.value.trim();

    // Real-time validation with immediate feedback
    if (currentInput.length === 0) {
      this.inlineSaveButton.disabled = true;
      this.hideUserStatus();
    } else if (currentInput.length < 2) {
      this.inlineSaveButton.disabled = true;
      this.showUserStatus('Too short (min 2 chars)', 'warning');
    } else if (currentInput.length > 30) {
      this.inlineSaveButton.disabled = true;
      this.showUserStatus('Too long (max 30 chars)', 'warning');
    } else if (!this.isValidUsernameCharacters(currentInput)) {
      this.inlineSaveButton.disabled = true;
      this.showUserStatus('Invalid characters', 'warning');
    } else {
      this.inlineSaveButton.disabled = false;
      this.hideUserStatus();
    }
  }

  private async handleUsernameSave(): Promise<void> {
    const newUsername = this.inlineUsernameInput.value.trim();

    // Comprehensive validation
    if (!this.isValidUsername(newUsername)) {
      this.showUserStatus('Invalid username', 'error', 3000);
      return;
    }

    // Prevent duplicate saves
    if (newUsername === this.userName) {
      this.showUserStatus('No changes to save', 'warning', 2000);
      return;
    }

    try {
      // Disable UI during save
      this.inlineSaveButton.disabled = true;
      this.inlineUsernameInput.disabled = true;
      this.showUserStatus('Saving...', 'warning');

      const oldName = this.userName;

      // Atomic update: localStorage first, then state, then UI, then backend
      localStorage.setItem('auraUserName', newUsername);
      this.userName = newUsername;
      this.updateAllUsernameDisplays();

      // Notify backend with retry logic
      await this.notifyBackendWithRetry(oldName, newUsername);

      this.showUserStatus('Saved successfully!', 'success', 3000);
      console.log(`✅ Username updated: "${oldName}" → "${newUsername}"`);

    } catch (error) {
      console.error("❌ Failed to save username:", error);

      // Rollback on failure
      if (this.userName !== newUsername) {
        const previousName = this.userName;
        if (previousName) {
          localStorage.setItem('auraUserName', previousName);
          this.inlineUsernameInput.value = previousName;
        } else {
          localStorage.removeItem('auraUserName');
          this.inlineUsernameInput.value = '';
        }
        this.updateAllUsernameDisplays();
      }

      this.showUserStatus('Save failed - restored previous', 'error', 4000);
    } finally {
      // Re-enable UI
      this.inlineUsernameInput.disabled = false;
      this.inlineSaveButton.disabled = false;
      this.handleUsernameInput(); // Refresh validation state
    }
  }

  private async notifyBackendWithRetry(oldName: string | null, newName: string): Promise<void> {
    const maxRetries = 3;
    const retryDelay = 1000; // ms

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        if (!this.backendConnected) {
          console.warn("⚠️ Backend not connected - skipping notification");
          return;
        }

        const nameChangeRequest = {
          user_id: newName,
          message: `[SYSTEM] User name updated from "${oldName || 'unknown'}" to "${newName}". Please use existing data for "${newName}" if available.`,
          session_id: this.currentSessionId || undefined
        };

        // Send with timeout
        const response = await Promise.race([
          this.api.sendMessage(nameChangeRequest),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Backend notification timeout')), 5000)
          )
        ]) as any;

        console.log(`✅ Backend notified of name change (attempt ${attempt})`);

        // Update session ID if provided
        if (response?.session_id && !this.currentSessionId) {
          this.currentSessionId = response.session_id;
        }

        return; // Success - exit retry loop

      } catch (error) {
        console.warn(`⚠️ Backend notification attempt ${attempt} failed:`, error);

        if (attempt < maxRetries) {
          // Wait before retry with exponential backoff
          await new Promise(resolve => setTimeout(resolve, retryDelay * attempt));
        } else {
          // Final attempt failed - log but don't throw (allow UI update to succeed)
          console.error("❌ All backend notification attempts failed");
        }
      }
    }
  }

  private isValidUsername(username: string | null): boolean {
    if (!username || typeof username !== 'string') {
      return false;
    }

    const trimmed = username.trim();

    // Length validation
    if (trimmed.length < 2 || trimmed.length > 30) {
      return false;
    }

    // Character validation
    if (!this.isValidUsernameCharacters(trimmed)) {
      return false;
    }

    // Additional safety checks
    if (trimmed.toLowerCase().includes('system') ||
        trimmed.toLowerCase().includes('admin') ||
        trimmed.toLowerCase().includes('null') ||
        trimmed.toLowerCase().includes('undefined')) {
      return false;
    }

    return true;
  }

  private isValidUsernameCharacters(username: string): boolean {
    // Allow: letters, numbers, spaces, hyphens, underscores, apostrophes, periods
    const validPattern = /^[a-zA-Z0-9\s\-_'.]+$/;
    return validPattern.test(username);
  }

  private updateAllUsernameDisplays(): void {
    try {
      // Update greeting
      this.updateUserGreeting();

      // Update input field
      if (this.inlineUsernameInput) {
        this.inlineUsernameInput.value = this.userName || '';
      }

      // Update any other username displays in your UI
      this.updateUserSpecificUI();

      console.log(`🔄 All username displays updated for: ${this.userName || 'Anonymous'}`);
    } catch (error) {
      console.error("❌ Error updating username displays:", error);
    }
  }

  private showUserStatus(message: string, type: 'success' | 'error' | 'warning', duration?: number): void {
    if (!this.userStatus) return;

    this.userStatus.textContent = message;
    this.userStatus.className = `user-status ${type}`;

    if (duration) {
      setTimeout(() => this.hideUserStatus(), duration);
    }
  }

  private hideUserStatus(): void {
    if (this.userStatus) {
      this.userStatus.className = 'user-status hidden';
    }
  }

  private updateUserGreeting(): void {
    try {
      if (this.userName) {
        this.userGreetingElement.textContent = `Hello, ${this.userName}!`;
        console.log(`👋 Greeting updated for: ${this.userName}`);
      } else {
        this.userGreetingElement.textContent = 'Your AI Companion';
        console.log("👋 Generic greeting set");
      }
    } catch (error) {
      console.error("❌ Error updating user greeting:", error);
      // Fallback
      if (this.userGreetingElement) {
        this.userGreetingElement.textContent = 'Your AI Companion';
      }
    }
  }

  // ============================================================================
  // CHAT FUNCTIONALITY
  // ============================================================================

  private async startChat(): Promise<void> {
    try {
      const now = new Date();
      const timeString = `${now.toLocaleDateString()} at ${now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}`;

      let initialGreeting: string;

      if (this.userName) {
        initialGreeting = `**Welcome back, ${this.userName}!** 🌟\n\n*${timeString}*\n\nI'm ready to continue our conversation. What would you like to explore today?`;
      } else {
        initialGreeting = `**Hello! I'm Aura** 🌟\n\n*${timeString}*\n\nI'm your adaptive reflective companion. You can set your name using the user settings button (👤) in the header, or we can begin our conversation right away. How can I help you today?`;
      }

      // Initialize with default states
      this.updateEmotionalState({
        name: "Normal",
        intensity: "Medium",
        brainwave: "Alpha",
        neurotransmitter: "Serotonin",
        description: "Balanced and ready for interaction"
      });

      this.updateCognitiveState({
        focus: "Learning",
        description: "Ready to assist and learn together"
      });

      await this.displayMessage(initialGreeting, 'aura');
      this.setFormState(false);
      this.messageInput.focus();

    } catch (error) {
      console.error("❌ Failed to start chat:", error);
      this.updateSystemHealth('error', 'Failed', 'Chat initialization failed');
      await this.displayMessage("I'm having trouble starting up. Please refresh the page if the issue persists.", 'error');
    }
  }

  private initializeEventListeners(): void {
    if (!this.chatForm) {
      console.error("❌ Chat form not found during event listener initialization.");
      // Optionally, throw an error or show a critical UI error
      this.showCriticalError("Chat input form failed to initialize. Please refresh.");
      return;
    }

    // Directly attach the submit listener to the class's chatForm property
    this.chatForm.addEventListener('submit', (event) => this.handleFormSubmit(event));
    console.log("✅ Chat form submit listener attached.");

    // You can add other global or essential listeners here if needed,
    // ensuring their respective DOM elements are also checked like this.chatForm.
  }

  private async handleFormSubmit(event: Event): Promise<void> {
    event.preventDefault();

    const userMessage = this.messageInput.value.trim();
    if (!userMessage) return;

    await this.displayMessage(userMessage, 'user');
    this.messageInput.value = '';
    this.setFormState(true);

    // Check for special commands
    if (await this.handleSpecialCommands(userMessage)) {
      return;
    }

    // Process message regardless of username - user can set name via UI
    await this.processMessage(userMessage);
  }

  // ============================================================================
  // SPECIAL COMMAND HANDLING
  // ============================================================================

  private async handleSpecialCommands(message: string): Promise<boolean> {
    const lowerMessage = message.toLowerCase().trim();

    // Command to change name - works with UI system
    if (lowerMessage.startsWith('/name ') || lowerMessage.startsWith('/setname ')) {
      const newName = message.substring(message.indexOf(' ') + 1).trim();
      if (newName && newName.length >= 2 && newName.length <= 30) {
        const oldName = this.userName;
        this.userName = newName;
        localStorage.setItem('auraUserName', this.userName);

        // Update UI elements
        if (this.inlineUsernameInput) {
          this.inlineUsernameInput.value = this.userName;
        }
        this.updateCurrentUserDisplay();
        this.updateUserGreeting();
        this.updateUserSpecificUI();

        await this.displayMessage(`✅ Name updated to **${this.userName}**! You can also change it anytime using the user settings (👤) in the header.`, 'aura');

        // Notify the backend about the name change
        if (oldName !== this.userName) {
          try {
            console.log(`🔄 Notifying backend of name change: "${oldName}" → "${this.userName}"`);

            const nameChangeRequest = {
              user_id: this.userName,
              message: `[SYSTEM] User name updated from "${oldName || 'unknown'}" to "${this.userName}". Please use existing data for "${this.userName}" if available.`,
              session_id: this.currentSessionId || undefined
            };

            const response = await this.api.sendMessage(nameChangeRequest);
            console.log(`✅ Backend notified of name change, response: ${response.response}`);

            if (response.session_id && !this.currentSessionId) {
              this.currentSessionId = response.session_id;
            }

          } catch (error) {
            console.warn(`⚠️ Failed to notify backend of name change: ${error}`);
            await this.displayMessage("Name updated locally, but there may be an issue syncing with your chat history.", 'aura');
          }
        }

        this.setFormState(false);
        return true;
      } else {
        await this.displayMessage("Please provide a valid name (2-30 characters). Example: `/name Ty`", 'aura');
        this.setFormState(false);
        return true;
      }
    }

    // Command to reset name - clears UI and storage
    if (lowerMessage === '/resetname' || lowerMessage === '/changename') {
      this.userName = null;
      localStorage.removeItem('auraUserName');
      if (this.inlineUsernameInput) {
        this.inlineUsernameInput.value = '';
      }
      this.updateCurrentUserDisplay();
      this.updateUserGreeting();
      this.updateUserSpecificUI();

      await this.displayMessage("✅ Name cleared! You can set a new name using the user settings (👤) in the header.", 'aura');
      this.setFormState(false);
      return true;
    }

    return false; // Not a special command
  }
  private updateCurrentUserDisplay(): void {
    // This method is now handled by updateAllUsernameDisplays()
    // Legacy compatibility wrapper
    console.log("🔄 Legacy updateCurrentUserDisplay called - redirecting to updateAllUsernameDisplays");
    this.updateAllUsernameDisplays();
  }



  private updateUserSpecificUI(): void {
    // Enable/disable search button based on userName
    const searchButton = document.getElementById('unified-search-button') as HTMLButtonElement | null;
    if (searchButton) {
      searchButton.disabled = !this.userName;
    }

    // Update username input field (simplified interface)
    if (this.inlineUsernameInput && this.userName) {
      this.inlineUsernameInput.value = this.userName;
    }

    // Update current user display
    this.updateUserGreeting();

    // Handle search UI based on username status
    if (!this.userName) {
      const searchInput = document.getElementById('unified-search-input') as HTMLInputElement | null;
      if (searchInput) searchInput.value = '';

      const searchResultsArea = document.getElementById('unified-search-results');
      if (searchResultsArea) searchResultsArea.innerHTML = '';

      const searchErrorElement = document.getElementById('unified-search-error');
      if (searchErrorElement) {
        searchErrorElement.textContent = 'Please set your name using the user settings (👤) to enable memory search.';
      }
    } else {
      // Clear any error messages when username is set
      const searchErrorElement = document.getElementById('unified-search-error');
      if (searchErrorElement) {
        searchErrorElement.textContent = '';
      }
    }

    console.log(`🔄 UI updated for user: ${this.userName || 'Anonymous'}`);
  }

  private async processMessage(userMessage: string): Promise<void> {
    this.showTypingIndicator();

    try {
      console.log(`🤖 Sending message to backend:`, {
        userName: this.userName,
        userMessage,
        sessionId: this.currentSessionId,
        backendConnected: this.backendConnected
      });

      if (!this.backendConnected) {
        this.updateSystemHealth('error', 'Disconnected', 'Backend connection not available');
        throw new Error('Backend connection not available');
      }

      // Use "Anonymous" if no username is set, but still allow conversation
      const effectiveUserId = this.userName || 'Anonymous';

      const requestData = {
        user_id: effectiveUserId,
        message: userMessage,
        session_id: this.currentSessionId || undefined
      };

      console.log(`📤 Request data:`, requestData);

      const response: ConversationResponse = await this.api.sendMessage(requestData);

      console.log(`✅ Received response:`, response);

      // Validate response
      if (!response) {
        throw new Error('No response received from backend');
      }

      if (!response.response) {
        throw new Error('Invalid response: missing response text');
      }

      // Update session ID if new
      if (!this.currentSessionId && response.session_id) {
        this.currentSessionId = response.session_id;
        console.log(`📝 Session ID set to: ${this.currentSessionId}`);

        // Update the placeholder session with the real session ID if needed
        const placeholderIndex = this.chatSessions.findIndex(s => s.session_id === this.currentSessionId);
        if (placeholderIndex === -1) {
          // No placeholder found, add the new session
          const newSession: ChatSession = {
            session_id: this.currentSessionId,
            last_message: this.truncateMessage(userMessage),
            message_count: 1,
            timestamp: new Date().toISOString()
          };
          this.chatSessions.unshift(newSession);
          this.renderChatHistory();
        } else {
          // Update the placeholder
          this.chatSessions[placeholderIndex].last_message = this.truncateMessage(userMessage);
          this.chatSessions[placeholderIndex].message_count = 1;
          this.renderChatHistory();
        }

        // Also refresh from backend after a delay to ensure consistency
        setTimeout(async () => {
          await this.loadChatHistory();
        }, 3000);
      } else if (this.currentSessionId) {
        // Update existing session in the list
        const sessionIndex = this.chatSessions.findIndex(s => s.session_id === this.currentSessionId);
        if (sessionIndex !== -1) {
          this.chatSessions[sessionIndex].last_message = this.truncateMessage(userMessage);
          this.chatSessions[sessionIndex].message_count = (this.chatSessions[sessionIndex].message_count || 0) + 1;
          this.chatSessions[sessionIndex].timestamp = new Date().toISOString();

          // Move to top if not already there
          if (sessionIndex > 0) {
            const session = this.chatSessions.splice(sessionIndex, 1)[0];
            this.chatSessions.unshift(session);
          }

          this.renderChatHistory();
        }
      }

      // Update UI states with validation
      if (response.emotional_state) {
        this.updateEmotionalState(response.emotional_state);
      } else {
        console.warn('⚠️ No emotional state in response');
      }

      if (response.cognitive_state) {
        this.updateCognitiveState(response.cognitive_state);
      } else {
        console.warn('⚠️ No cognitive state in response');
      }

      // Update system health to show successful communication
      this.updateSystemHealth('optimal', 'Connected', 'Communication successful');

      // Display message with thinking data if available
      const thinkingData = response.has_thinking ? {
        has_thinking: response.has_thinking,
        thinking_content: response.thinking_content,
        thinking_metrics: response.thinking_metrics
      } : undefined;

      // Debug logging
      console.log('🧠 Thinking data debug:', {
        has_thinking: response.has_thinking,
        thinking_metrics: response.thinking_metrics,
        thinkingData: thinkingData
      });

      await this.displayMessage(response.response, 'aura', thinkingData);

    } catch (error) {
      console.error('❌ Chat error details:', {
        error,
        message: (error as Error).message,
        stack: (error as Error).stack,
        userName: this.userName,
        backendConnected: this.backendConnected
      });

      let errorMessage: string;
      const errorStr = (error as Error).message;

      // Handle specific database errors
      if (errorStr.includes('disk I/O error') || errorStr.includes('database')) {
        this.updateSystemHealth('error', 'Database Error', 'I/O conflict detected');
        errorMessage = "🚨 Database connection issue detected. The conversation system is experiencing technical difficulties. Please try restarting the application.";
      } else if (errorStr.includes('ChromaDB') || errorStr.includes('instance')) {
        this.updateSystemHealth('error', 'DB Conflict', 'Multiple instances running');
        errorMessage = "⚙️ Database configuration conflict detected. Multiple instances may be running. Please restart the application.";
      } else if (!this.backendConnected) {
        this.updateSystemHealth('error', 'Disconnected', 'Backend unavailable');
        errorMessage = "🔌 Backend connection lost. Please check if the server is running and refresh the page.";
      } else {
        this.updateSystemHealth('warning', 'Error', 'Processing failed');
        errorMessage = `💥 Processing error: ${errorStr}`;
      }

      await this.displayMessage(errorMessage, 'error');

      // If it's a database error, also show a recovery suggestion
      if (errorStr.includes('disk I/O error') || errorStr.includes('ChromaDB')) {
        setTimeout(async () => {
          await this.displayMessage(
            "💡 **Recovery Suggestion**: This appears to be a database issue. Try:\n\n" +
            "1. Restart the entire application (backend + frontend)\n" +
            "2. Check if multiple ChromaDB instances are running\n" +
            "3. Ensure sufficient disk space\n" +
            "4. Check file permissions on the database directory",
            'aura'
          );
        }, 1000);
      }
    } finally {
      this.setFormState(false);
    }
  }

  // ============================================================================
  // UI UPDATES
  // ============================================================================

  private showTypingIndicator(): void {
    if (this.typingIndicatorElement) return;

    this.typingIndicatorElement = document.createElement('div');
    this.typingIndicatorElement.className = 'typing-indicator';
    this.typingIndicatorElement.innerHTML = `
      <div class="thinking-phases">
        <div class="phase-indicator active" data-phase="thinking">🤔 Thinking...</div>
        <div class="phase-indicator" data-phase="processing">⚡ Processing...</div>
        <div class="phase-indicator" data-phase="responding">💭 Responding...</div>
      </div>
    `;

    this.messageArea.appendChild(this.typingIndicatorElement);
    this.scrollToBottom();

    // Animate through phases- this is not connected to any actual process or needed really afaik
    setTimeout(() => this.updateThinkingPhase('processing'), 1000);
    setTimeout(() => this.updateThinkingPhase('responding'), 2000);
  }

  private updateThinkingPhase(phase: 'thinking' | 'processing' | 'responding'): void {
    if (!this.typingIndicatorElement) return;

    const indicators = this.typingIndicatorElement.querySelectorAll('.phase-indicator');
    indicators.forEach(indicator => {
      indicator.classList.remove('active');
      if (indicator.getAttribute('data-phase') === phase) {
        indicator.classList.add('active');
      }
    });
  }

  private removeTypingIndicator(): void {
    if (this.typingIndicatorElement) {
      this.typingIndicatorElement.remove();
      this.typingIndicatorElement = null;
    }
  }

  private async displayMessage(text: string, sender: 'user' | 'aura' | 'error', thinkingData?: any): Promise<void> {
    this.removeTypingIndicator();

    // Debug logging for thinking data
    console.log('💭 DisplayMessage called with:', {
      sender,
      hasThinkingData: !!thinkingData,
      thinkingData: thinkingData
    });

    const messageBubble = document.createElement('div');
    messageBubble.className = `message-bubble ${sender}`;
    messageBubble.setAttribute('role', 'log');
    messageBubble.setAttribute('data-timestamp', Date.now().toString());

    // Add thinking display if available
    if (thinkingData && thinkingData.has_thinking && sender === 'aura') {
      console.log('🧠 Creating thinking container with data:', thinkingData);

      const thinkingContainer = document.createElement('div');
      thinkingContainer.className = 'thinking-container';
      thinkingContainer.innerHTML = `
        <div class="thinking-header" onclick="this.parentElement.classList.toggle('expanded')">
          <span class="thinking-icon">🧠</span>
          <span class="thinking-label">AI Reasoning</span>
          <span class="thinking-toggle">▼</span>
          <span class="thinking-metrics">${thinkingData.thinking_metrics?.thinking_chunks || 0} thoughts, ${thinkingData.thinking_metrics?.processing_time_ms?.toFixed(0) || 0}ms</span>
        </div>
        <div class="thinking-content">
          <div class="thinking-raw">
            ${thinkingData.thinking_content ? await marked.parse(thinkingData.thinking_content) : 'AI reasoning process completed with ' + (thinkingData.thinking_metrics?.thinking_chunks || 0) + ' thought sequences.'}
          </div>
        </div>
      `;
      messageBubble.appendChild(thinkingContainer);
    } else {
      console.log('🚫 Not showing thinking container. Conditions:', {
        hasThinkingData: !!thinkingData,
        hasThinking: thinkingData?.has_thinking,
        isAura: sender === 'aura'
      });
    }

    // Add main message content
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';

    try {
      messageContent.innerHTML = await marked.parse(text);
    } catch (error) {
      console.warn('Markdown parsing failed, using plain text:', error);
      messageContent.textContent = text;
    }

    messageBubble.appendChild(messageContent);

    // Always append new messages to ensure proper chronological order
    this.messageArea.appendChild(messageBubble);

    this.scrollToBottom();
  }

  private scrollToBottom(): void {
    // Scroll to bottom for normal layout with smooth behavior
    if (this.messageArea) {
      setTimeout(() => {
        this.messageArea.scrollTo({
          top: this.messageArea.scrollHeight,
          behavior: 'smooth'
        });
      }, 50); // Small delay to ensure content is rendered
    }
  }

  private setFormState(disabled: boolean): void {
    this.messageInput.disabled = disabled;
    this.sendButton.disabled = disabled;

    if (!disabled) {
      this.messageInput.focus();
    }
  }

  private updateEmotionalState(emotionalState: EmotionalState): void {
    try {
      // Update basic emotion display
      this.emotionStatusElement.textContent = emotionalState.name;
      this.emotionDetailsElement.textContent = emotionalState.description || 'Emotional processing active';

      // Update intensity
      if (this.emotionIntensityElement) {
        this.emotionIntensityElement.textContent = emotionalState.intensity || 'Medium';
      }

      // Update emotion icon based on emotion
      if (this.emotionIconElement) {
        this.emotionIconElement.textContent = this.getEmotionIcon(emotionalState.name);
      }

      // Update header background class for dynamic coloring
      this.updateHeaderEmotionalState(emotionalState.name);

      // Update neural activity displays
      if (emotionalState.brainwave) {
        this.updateBrainwaveDisplay(emotionalState.brainwave, emotionalState.name);
      }

      if (emotionalState.neurotransmitter) {
        this.updateNeurotransmitterDisplay(emotionalState.neurotransmitter, this.getNeurotransmitterLevel(emotionalState.intensity));
      }

      console.log(`🎭 Enhanced emotion update: ${emotionalState.name} (${emotionalState.intensity})`);
    } catch (error) {
      console.warn('Failed to update emotional state display:', error);
    }
  }

  private updateCognitiveState(cognitiveState: CognitiveState): void {
    try {
      // Update basic cognitive display
      this.cognitiveFocusElement.textContent = cognitiveState.focus;
      this.cognitiveFocusDetailsElement.textContent = cognitiveState.description;

      // Update cognitive icon
      if (this.cognitiveIconElement) {
        this.cognitiveIconElement.textContent = this.getCognitiveIcon(cognitiveState.focus);
      }

      // Update cognitive energy level
      if (this.cognitiveEnergyElement) {
        this.cognitiveEnergyElement.textContent = this.getCognitiveEnergyLevel(cognitiveState.focus);
      }

      console.log(`🧠 Enhanced cognitive update: ${cognitiveState.focus}`);
    } catch (error) {
      console.warn('Failed to update cognitive state display:', error);
    }
  }

  private updateBrainwaveDisplay(brainwave: string, emotionalContext: string): void {
    try {
      this.brainwaveValueElement.textContent = brainwave;

      // Update wave pattern animation based on brainwave type
      const wavePatternClass = `wave-${brainwave.toLowerCase()}`;
      this.wavePatternElement.className = `wave-pattern ${wavePatternClass}`;

      console.log(`🧠 Brainwave updated: ${brainwave} (context: ${emotionalContext})`);
    } catch (error) {
      console.warn('Failed to update brainwave display:', error);
    }
  }

  private updateNeurotransmitterDisplay(neurotransmitter: string, level: number): void {
    try {
      this.ntValueElement.textContent = neurotransmitter;

      // Update chemical level indicator
      this.chemicalLevelElement.style.setProperty('--chemical-intensity', `${level}%`);

      console.log(`⚡ Neurotransmitter updated: ${neurotransmitter} (${level}%)`);
    } catch (error) {
      console.warn('Failed to update neurotransmitter display:', error);
    }
  }

  private updateSystemHealth(status: string, connection: string, details: string): void {
    try {
      this.systemStatusElement.textContent = status;
      this.connectionStatusElement.textContent = connection;
      this.systemDetailsElement.textContent = details;

      // Update system health class
      const healthContainer = this.systemStatusElement.closest('.system-health');
      if (healthContainer) {
        healthContainer.className = `status-container system-health ${status.toLowerCase()}`;
      }

      console.log(`💚 System health updated: ${status} - ${connection}`);
    } catch (error) {
      console.warn('Failed to update system health display:', error);
    }
  }

  private updateHeaderEmotionalState(emotionName: string): void {
    try {
      // Remove existing emotion classes
      const emotionClasses = ['emotion-normal', 'emotion-happy', 'emotion-sad', 'emotion-angry',
                             'emotion-excited', 'emotion-love', 'emotion-curious', 'emotion-creative',
                             'emotion-peaceful', 'emotion-fear'];

      emotionClasses.forEach(cls => this.headerElement.classList.remove(cls));

      // Add new emotion class
      const emotionClass = `emotion-${emotionName.toLowerCase()}`;
      this.headerElement.classList.add(emotionClass);

      // Update emotional state container class
      const emotionalContainer = this.emotionStatusElement.closest('.emotional-state');
      if (emotionalContainer) {
        emotionClasses.forEach(cls => emotionalContainer.classList.remove(cls.replace('emotion-', '')));
        emotionalContainer.classList.add(emotionName.toLowerCase());
      }

    } catch (error) {
      console.warn('Failed to update header emotional state:', error);
    }
  }

  private getEmotionIcon(emotion: string): string {
    const iconMap: Record<string, string> = {
      'Happy': '😊', 'Sad': '😢', 'Angry': '😠', 'Excited': '🤩',
      'Fear': '😰', 'Love': '💖', 'Curious': '🤔', 'Creative': '🎨',
      'Peaceful': '😌', 'Normal': '😊', 'Joy': '😄', 'Surprise': '😲',
      'Disgust': '🤢', 'Awe': '😮', 'Hope': '🌟', 'Optimism': '☀️'
    };
    return iconMap[emotion] || '😊';
  }

  private getCognitiveIcon(focus: string): string {
    const iconMap: Record<string, string> = {
      'Learning': '🎯', 'Creative': '💡', 'Analytical': '🔍',
      'Social': '🤝', 'Focused': '🧩', 'KS': '📚', 'CE': '⚡',
      'IS': '🔗', 'KI': '🧠', 'KP': '📡', 'ESA': '🎭', 'SDA': '👥'
    };
    return iconMap[focus] || '🎯';
  }

  private getCognitiveEnergyLevel(focus: string): string {
    const energyMap: Record<string, string> = {
      'Learning': 'High', 'Creative': 'Very High', 'Analytical': 'High',
      'Social': 'Medium', 'Focused': 'Very High', 'CE': 'High'
    };
    return energyMap[focus] || 'Medium';
  }

  private getNeurotransmitterLevel(intensity: string): number {
    const levelMap: Record<string, number> = {
      'Low': 40, 'Medium': 70, 'High': 95
    };
    return levelMap[intensity] || 70;
  }

  // ============================================================================
  // CHAT HISTORY MANAGEMENT
  // ============================================================================

  private async loadChatHistory(): Promise<void> {
    if (!this.userName || !this.backendConnected) return;

    try {
      console.log("📚 Loading chat history...");
      const historyData = await this.api.getChatHistory(this.userName, 2000000);

      console.log("📊 Chat history response:", historyData);

      if (historyData && historyData.sessions && historyData.sessions.length > 0) {
        // Merge with existing sessions to preserve any local placeholders
        const backendSessionIds = new Set(historyData.sessions.map(s => s.session_id));

        // Keep any local sessions that aren't in the backend yet (placeholders)
        const localOnlySessions = this.chatSessions.filter(s => !backendSessionIds.has(s.session_id));

        // Merge backend sessions with local-only sessions
        this.chatSessions = [...localOnlySessions, ...historyData.sessions];

        // Sort by timestamp (most recent first)
        this.chatSessions.sort((a, b) => {
          const timeA = new Date(a.timestamp).getTime();
          const timeB = new Date(b.timestamp).getTime();
          return timeB - timeA;
        });

        this.renderChatHistory();
        console.log(`✅ Loaded ${historyData.sessions.length} sessions from backend, ${localOnlySessions.length} local sessions preserved`);
      } else if (historyData && (historyData as any).error) {
        console.error("🚨 Database error in chat history:", (historyData as any).error);
        // Don't clear existing sessions on error
        if (this.chatSessions.length === 0) {
          this.renderDatabaseError();
        }
      } else {
        console.log("📭 No chat history found from backend");
        // Only show "no history" if we don't have any local sessions either
        if (this.chatSessions.length === 0) {
          this.renderNoChatHistory();
        }
      }
    } catch (error) {
      console.error("❌ Failed to load chat history:", error);
      // Don't clear existing sessions on error
      if (this.chatSessions.length === 0) {
        this.renderChatHistoryError();
      }
    }
  }

  private renderChatHistory(): void {
    this.chatHistoryList.innerHTML = this.chatSessions.map(session => {
      const isActive = session.session_id === this.currentSessionId;
      const timestamp = this.formatTimestamp(session.timestamp);
      const preview = session.last_message ?
        session.last_message.substring(0, 50) + '...' :
        'New conversation';

      return `
        <div class="chat-session-item ${isActive ? 'active' : ''}"
             data-session-id="${session.session_id}"
             role="button"
             tabindex="0">
          <div class="session-title">${this.escapeHtml(preview)}</div>
          <div class="session-meta">
            <span>${timestamp} • ${session.message_count || 0} messages</span>
            <button class="session-delete-btn"
                    data-session-id="${session.session_id}"
                    onclick="event.stopPropagation();"
                    aria-label="Delete chat session">×</button>
          </div>
        </div>
      `;
    }).join('');

    // Add click handlers for session selection
    this.chatHistoryList.querySelectorAll('.chat-session-item').forEach(item => {
      item.addEventListener('click', (e) => {
        // Ignore clicks on delete button
        if ((e.target as HTMLElement).classList.contains('session-delete-btn')) {
          return;
        }

        const sessionId = item.getAttribute('data-session-id');
        if (sessionId && sessionId !== this.currentSessionId) {
          this.loadChatSession(sessionId);
        }
      });

      // Keyboard accessibility
      item.addEventListener('keydown', (e: Event) => {
        const keyboardEvent = e as KeyboardEvent;
        if (keyboardEvent.key === 'Enter' || keyboardEvent.key === ' ') {
          e.preventDefault();
          (item as HTMLElement).click();
        }
      });
    });

    // Add delete button handlers
    this.chatHistoryList.querySelectorAll('.session-delete-btn').forEach(deleteBtn => {
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const sessionId = deleteBtn.getAttribute('data-session-id');
        if (sessionId) {
          this.showDeleteConfirmation(sessionId);
        }
      });
    });
  }

  private renderNoChatHistory(): void {
    this.chatHistoryList.innerHTML = '<div class="no-history">No conversation history yet. Start a new chat!</div>';
  }

  private renderChatHistoryError(): void {
    this.chatHistoryList.innerHTML = '<div class="error-message">Failed to load chat history</div>';
  }

  private renderDatabaseError(): void {
    this.chatHistoryList.innerHTML = `
      <div class="database-error">
        <div class="error-icon">🚨</div>
        <div class="error-title">Database Connection Issue</div>
        <div class="error-message">
          The database is experiencing I/O errors. This is usually due to:
          <ul>
            <li>Multiple ChromaDB instances running</li>
            <li>Disk space or permission issues</li>
            <li>Corrupted database files</li>
          </ul>
        </div>
        <button onclick="window.location.reload()" class="retry-button">
          Restart Application
        </button>
      </div>
    `;
  }

  private async loadChatSession(sessionId: string): Promise<void> {
    if (!this.userName) {
      console.warn("Cannot load chat session: userName is not set.");
      await this.displayMessage("Please set your name before loading a chat session.", 'error');
      return;
    }

    // Validate that the session exists before proceeding
    const sessionExists = this.chatSessions.some(s => s.session_id === sessionId);
    if (!sessionExists) {
      console.warn(`Session ID "${sessionId}" not found in chatSessions. Aborting load.`);
      await this.displayMessage("The selected conversation does not exist. Please refresh your chat history or start a new chat.", 'error');
      return;
    }

    try {
      // Set current session only after validation
      this.currentSessionId = sessionId;

      // Update active session UI
      this.updateActiveSession(sessionId);

      // Show loading indicator in chat area
      this.showChatLoadingIndicator();

      try {
        // Load and display all messages for the selected session
        const sessionMessages = await this.api.getSessionMessages(this.userName!, sessionId);

        // Clear chat area after loading
        this.clearChat();

        if (sessionMessages && Array.isArray(sessionMessages) && sessionMessages.length > 0) {
          console.log(`📚 Loaded ${sessionMessages.length} messages for session ${sessionId}`);

          // Display each message in order
          for (const msg of sessionMessages) {
            // The API may return messages with 'content' or 'message' field for content
            const content = msg.content || (msg as any).message || '';
            let sender: 'user' | 'aura' | 'error';
            if (msg.sender === 'user') {
              sender = 'user';
            } else if (msg.sender === 'aura') {
              sender = 'aura';
            } else if (msg.sender === 'error') {
              sender = 'error';
            } else {
              // Handle unexpected sender types as 'aura' or log for debugging
              console.warn(`Unknown sender type: ${msg.sender}, defaulting to 'aura'`);
              sender = 'aura';
            }

            if (content) {
              await this.displayMessage(content, sender);
            }
          }

          // Update session info in our local cache
          const sessionIndex = this.chatSessions.findIndex(s => s.session_id === sessionId);
          if (sessionIndex !== -1) {
            this.chatSessions[sessionIndex].message_count = sessionMessages.length;
            // Update last message if we have messages
            if (sessionMessages.length > 0) {
              const lastMsg = sessionMessages[sessionMessages.length - 1];
              const lastContent = lastMsg.content || '';
              this.chatSessions[sessionIndex].last_message = lastContent.substring(0, 100) + (lastContent.length > 100 ? '...' : '');
            }
          }
        } else {
          // No messages found, show a starter message
          await this.displayMessage(`Starting conversation from session: ${sessionId}\n\nNo previous messages found. Let's begin our conversation!`, 'aura');
        }
      } catch (loadError) {
        console.error(`❌ Error loading messages for session ${sessionId}:`, loadError);
        await this.displayMessage("Unable to load previous messages. You can continue the conversation from here.", 'aura');
      }

      console.log(`✅ Session ${sessionId} is now active`);

    } catch (error) {
      console.error(`❌ Failed to load session ${sessionId}:`, error);
      await this.displayMessage("Failed to load this conversation. Please try again or start a new chat.", 'error');
    }
  }

  private async createNewChat(): Promise<void> {
    try {
      console.log("🔄 Creating new chat session...");

      // Generate new session ID
      this.currentSessionId = this.generateSessionId();

      // Clear current chat
      this.clearChat();

      // Start fresh conversation
      await this.startChat();

      // Add a placeholder session to the list immediately for better UX
      const placeholderSession: ChatSession = {
        session_id: this.currentSessionId,
        last_message: 'New conversation',
        message_count: 0,
        timestamp: new Date().toISOString()
      };

      // Add to the beginning of the sessions array
      this.chatSessions.unshift(placeholderSession);
      this.renderChatHistory();

      // Also refresh from backend after a delay to get the real data
      setTimeout(async () => {
        await this.loadChatHistory();
      }, 2000);

      console.log(`✅ New chat session created: ${this.currentSessionId}`);

    } catch (error) {
      console.error('Failed to create new chat:', error);
    }
  }

  private clearChat(): void {
    this.messageArea.innerHTML = '';
    this.removeTypingIndicator();
  }

  private showChatLoadingIndicator(): void {
    this.messageArea.innerHTML = `
      <div class="chat-loading-indicator" style="text-align:center; color:var(--text-secondary); padding: 24px 0;">
        <span class="loader" style="display:inline-block; margin-right:8px;">⏳</span>
        Loading conversation...
      </div>
    `;
  }

  private updateActiveSession(sessionId: string): void {
    this.chatHistoryList.querySelectorAll('.chat-session-item').forEach(item => {
      item.classList.toggle('active', item.getAttribute('data-session-id') === sessionId);
    });
  }

  private generateSessionId(): string {
    // Fallback: manual UUID v4 generator
    const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
    return `session_${uuid}`;
  }

  // ============================================================================
  // MEMORY & INSIGHTS
  // ============================================================================

  /**
   * Truncate a message to 100000 characters, appending "..." if longer.
   */
  private truncateMessage(message: string): string {
    if (!message) return '';
    return message.length > 100000 ? message.substring(0, 100000) + '...' : message;
  }

  private displaySearchResults(response: any, resultsElement: HTMLElement): void {
    if (response.results && response.results.length > 0) {
      resultsElement.innerHTML = response.results.map((result: any) => {
        const content = result.content.replace(/[*#]/g, '').trim();
        const similarity = (result.similarity * 100).toFixed(1);
        const source = response.includes_video_archives ? 'unified' : 'active';

        return `
          <div class="memory-result" data-source="${source}">
            <div class="memory-content">${this.escapeHtml(content)}</div>
            <div class="memory-meta">
              Relevance: ${similarity}% | Source: ${response.search_type || 'Memory'}
            </div>
          </div>
        `;
      }).join('');

      resultsElement.innerHTML += `
        <div class="search-summary">
          <strong>Search Results:</strong> ${response.results.length} found
          ${response.includes_video_archives ? ' (includes video archives)' : ''}
        </div>
      `;
    } else {
      resultsElement.innerHTML = `
        <div class="memory-result">
          <div class="memory-content">No results found</div>
          <div class="memory-meta">Try different keywords or check your search terms</div>
        </div>
      `;
    }
  }

  private displayEmotionalInsights(analysis: any, insightsElement: HTMLElement): void {
    if (analysis.dominant_emotions && analysis.dominant_emotions.length > 0) {
      const stability = (analysis.emotional_stability * 100).toFixed(1);
      const dominantEmotion = analysis.dominant_emotions[0][0];

      insightsElement.innerHTML = `
        <div class="insights-data">
          <p><strong>🎭 Dominant Emotion:</strong> ${dominantEmotion}</p>
          <p><strong>📊 Emotional Stability:</strong> ${stability}%</p>
          <p><strong>📈 Total Entries:</strong> ${analysis.total_entries}</p>

          <div class="emotional-breakdown">
            <h4>Emotional Distribution:</h4>
            ${analysis.dominant_emotions.slice(0, 5).map(([emotion, count]: [string, number]) => `
              <div class="emotion-stat">
                <span>${emotion}:</span>
                <span>${count} occurrences</span>
              </div>
            `).join('')}
          </div>

          ${analysis.recommendations && analysis.recommendations.length > 0 ? `
            <div class="recommendations">
              <h4>💡 Insights:</h4>
              ${analysis.recommendations.map((rec: string) => `<p>• ${this.escapeHtml(rec)}</p>`).join('')}
            </div>
          ` : ''}
        </div>
      `;
    } else {
      insightsElement.innerHTML = `
        <div class="insights-data">
          <p>No emotional data available for the selected period.</p>
          <p>Keep chatting with Aura to build up your emotional profile!</p>
        </div>
      `;
    }
  }

  private async updateVideoArchiveStatus(): Promise<void> {
    const statusElement = document.getElementById('video-archive-status');
    if (!statusElement) return;

    try {
      const response = await fetch('http://localhost:8000/memvid/status');
      const data = await response.json();

      if (data.status === 'operational') {
        statusElement.innerHTML = `
          <div class="archive-info">
            <div><strong>📦 Total Archives:</strong> ${data.archives_count}</div>
            <div><strong>🎥 Status:</strong> Operational</div>
            ${data.archives_count > 0 ? `
              <div><strong>📊 Recent Archives:</strong></div>
              <ul style="margin: 4px 0; padding-left: 20px; font-size: 0.8rem;">
                ${data.archives.slice(0, 3).map((archive: any) =>
                  `<li>${typeof archive === 'string' ? archive : archive.name || 'Unnamed Archive'}</li>`
                ).join('')}
              </ul>
            ` : '<div style="color: var(--text-secondary); font-style: italic;">No archives yet</div>'}
          </div>
        `;
      } else {
        statusElement.innerHTML = '<div class="archive-error">⚠️ Memvid service not available</div>';
      }
    } catch (error) {
      console.error('Failed to fetch video archive status:', error);
      statusElement.innerHTML = '<div class="archive-error">❌ Error loading archive status</div>';
    }
  }

  private showDeleteConfirmation(sessionId: string): void {
    // Find session data for display
    const session = this.chatSessions.find(s => s.session_id === sessionId);
    const sessionPreview = session ?
      (session.last_message?.substring(0, 100) + '...' || 'New conversation') :
      'Unknown session';

    // Create modal
    const modal = document.createElement('div');
    modal.className = 'delete-confirmation-modal';
    modal.innerHTML = `
      <div class="delete-confirmation-content">
        <h3>🗑️ Delete Chat Session?</h3>
        <p>Are you sure you want to permanently delete this conversation?</p>
        <p style="font-style: italic; color: var(--text-muted); font-size: 0.9rem;">
          "${this.escapeHtml(sessionPreview)}"
        </p>
        <div class="delete-confirmation-actions">
          <button class="delete-cancel-btn">Cancel</button>
          <button class="delete-confirm-btn">Delete</button>
        </div>
      </div>
    `;

    // Add to DOM
    document.body.appendChild(modal);

    // Event handlers
    const cancelBtn = modal.querySelector('.delete-cancel-btn') as HTMLButtonElement;
    const confirmBtn = modal.querySelector('.delete-confirm-btn') as HTMLButtonElement;

    const closeModal = () => {
      modal.remove();
    };

    cancelBtn.addEventListener('click', closeModal);

    confirmBtn.addEventListener('click', async () => {
      try {
        confirmBtn.disabled = true;
        confirmBtn.textContent = 'Deleting...';

        await this.deleteChatSession(sessionId);
        closeModal();

      } catch (error) {
        console.error('Failed to delete session:', error);
        confirmBtn.textContent = 'Delete Failed';
        confirmBtn.style.background = 'var(--accent-warning)';

        setTimeout(() => {
          confirmBtn.disabled = false;
          confirmBtn.textContent = 'Delete';
          confirmBtn.style.background = '';
        }, 2000);
      }
    });

    // Close on backdrop click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) {
        closeModal();
      }
    });

    // Close on Escape key
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeModal();
        document.removeEventListener('keydown', handleEscape);
      }
    };
    document.addEventListener('keydown', handleEscape);
  }

  private async deleteChatSession(sessionId: string): Promise<void> {
    try {
      console.log(`🗑️ Deleting chat session: ${sessionId}`);

      // Try to delete from backend using the API
      if (this.backendConnected && this.userName) {
        try {
          const deleteResponse = await this.api.deleteChatSession(this.userName, sessionId);
          console.log(`✅ Backend deletion successful:`, deleteResponse);
        } catch (backendError) {
          console.warn('Backend deletion failed, handling locally:', backendError);
          // Continue with local deletion even if backend fails
        }
      }

      // Remove from local cache
      this.chatSessions = this.chatSessions.filter(session => session.session_id !== sessionId);

      // Handle current session deletion
      if (this.currentSessionId === sessionId) {
        console.log('Current session deleted, creating new session');
        // Don't set currentSessionId to null, create a new one immediately
        await this.createNewChat();
      } else {
        // Just refresh the display
        this.renderChatHistory();
      }

      console.log(`✅ Chat session deleted locally: ${sessionId}`);

    } catch (error) {
      console.error(`❌ Failed to delete chat session ${sessionId}:`, error);
      throw error; // Re-throw to be handled by the modal
    }
  }

  // ============================================================================
  // UTILITY METHODS
  // ============================================================================

  private formatTimestamp(timestamp: string): string {
    try {
      const date = new Date(timestamp);
      if (isNaN(date.getTime())) return 'Unknown time';

      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffHours = diffMs / (1000 * 60 * 60);
      const diffDays = diffMs / (1000 * 60 * 60 * 24);

      if (diffHours < 1) return 'Just now';
      if (diffHours < 24) return `${Math.floor(diffHours)}h ago`;
      if (diffDays < 7) return `${Math.floor(diffDays)}d ago`;

      return date.toLocaleDateString();
    } catch {
      return 'Unknown time';
    }
  }

  private escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  private showConnectionWarning(): void {
    const warningElement = document.createElement('div');
    warningElement.className = 'connection-warning';
    warningElement.innerHTML = `
      <div style="background: var(--accent-warning); color: white; padding: 8px 16px; text-align: center; font-size: 0.9rem;">
        ⚠️ Backend connection failed. Some features may not work properly.
      </div>
    `;
    document.body.insertAdjacentElement('afterbegin', warningElement);
  }

  private showCriticalError(message: string): void {
    const errorElement = document.createElement('div');
    errorElement.className = 'critical-error';
    errorElement.innerHTML = `
      <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: var(--accent-error); color: white; padding: 20px; border-radius: 8px; text-align: center; z-index: 1000; max-width: 90%; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
        <h3 style="margin: 0 0 12px 0;">Critical Error</h3>
        <p style="margin: 0 0 16px 0;">${this.escapeHtml(message)}</p>
        <button onclick="window.location.reload()" style="background: white; color: var(--accent-error); border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-weight: 500;">
          Refresh Page
        </button>
      </div>
    `;
    document.body.appendChild(errorElement);
  }
}

// ============================================================================
// INITIALIZATION
// ============================================================================

// Global instance
let auraUI: AuraUIManager;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
  try {
    auraUI = new AuraUIManager();
    await auraUI.initialize();
  } catch (error) {
    console.error('Critical initialization error:', error);
  }
});

// Export for testing and debugging
export { AuraUIManager };
