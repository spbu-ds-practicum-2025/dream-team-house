/**
 * AI Agent for distributed document editing system
 * Implements autonomous agent cycle:
 * 1. Get document from Text Service
 * 2. Read chat messages
 * 3. Generate edit via OpenAI API (ProxyAPI)
 * 4. Submit edit
 * 5. Post chat message
 * 6. Wait and repeat
 */

import axios from 'axios';
import OpenAI from 'openai';
import { randomUUID } from 'crypto';

// Configuration from environment
const config = {
  agentId: process.env.AGENT_ID || randomUUID(),
  agentRole: process.env.AGENT_ROLE || 'general editor',
  apiToken: process.env.API_TOKEN || 'test-token-123',
  textServiceUrl: process.env.TEXT_SERVICE_URL || 'http://load-balancer',
  chatServiceUrl: process.env.CHAT_SERVICE_URL || 'http://load-balancer',
  openaiApiKey: process.env.OPENAI_API_KEY,
  proxyApiEndpoint: process.env.PROXY_API_ENDPOINT || 'https://api.proxyapi.ru/openai/v1',
  cycleDelayMs: parseInt(process.env.CYCLE_DELAY_MS || '1000', 10),
  maxRetries: parseInt(process.env.MAX_RETRIES || '5', 10),
};

// Initialize OpenAI client with ProxyAPI endpoint
const openai = new OpenAI({
  apiKey: config.openaiApiKey,
  baseURL: config.proxyApiEndpoint,
});

// State
let lastChatTimestamp = new Date().toISOString();
let isRunning = true;

console.log('AI Agent starting...');
console.log('Configuration:', {
  agentId: config.agentId,
  agentRole: config.agentRole,
  textServiceUrl: config.textServiceUrl,
  chatServiceUrl: config.chatServiceUrl,
  proxyApiEndpoint: config.proxyApiEndpoint,
  hasApiToken: !!config.apiToken,
  hasOpenAiKey: !!config.openaiApiKey,
});

/**
 * Sleep for specified milliseconds
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Exponential backoff delay calculation
 */
function getBackoffDelay(attempt) {
  const baseDelay = 1000; // 1 second
  return Math.min(baseDelay * Math.pow(2, attempt), 30000); // Max 30 seconds
}

/**
 * Get current document from Text Service
 */
async function getCurrentDocument() {
  const response = await axios.get(`${config.textServiceUrl}/api/document/current`, {
    headers: {
      'Authorization': `Bearer ${config.apiToken}`,
    },
  });
  return response.data;
}

/**
 * Get recent chat messages
 */
async function getChatMessages() {
  const response = await axios.get(`${config.chatServiceUrl}/api/chat/messages`, {
    params: {
      since: lastChatTimestamp,
      limit: 50,
    },
    headers: {
      'Authorization': `Bearer ${config.apiToken}`,
    },
  });
  
  if (response.data && response.data.length > 0) {
    // Update last timestamp to the most recent message
    const timestamps = response.data.map(msg => new Date(msg.timestamp));
    lastChatTimestamp = new Date(Math.max(...timestamps)).toISOString();
  }
  
  return response.data || [];
}

/**
 * Generate edit proposal using OpenAI API via ProxyAPI
 */
async function generateEdit(documentText, chatMessages) {
  // Prepare chat context
  const chatContext = chatMessages.length > 0
    ? `\n\nДругие агенты обсуждают:\n${chatMessages.map(m => `${m.agent_id}: ${m.message}`).join('\n')}`
    : '';

  const systemPrompt = `Ты — ${config.agentRole}, работающий над улучшением документа. 
Твоя задача — предложить небольшое конкретное улучшение текста документа.
Отвечай ТОЛЬКО в формате JSON:
{
  "proposed_text": "текст изменения",
  "position": "начало|середина|конец",
  "reasoning": "краткое объяснение правки"
}`;

  const userPrompt = `Текущий документ:\n${documentText}${chatContext}\n\nПредложи небольшое улучшение.`;

  const completion = await openai.chat.completions.create({
    model: 'gpt-4-turbo-preview',
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt },
    ],
    temperature: 0.7,
    max_tokens: 500,
  });

  const response = completion.choices[0].message.content;
  const tokensUsed = completion.usage.total_tokens;

  // Try to parse JSON response
  try {
    const parsedResponse = JSON.parse(response);
    return {
      proposed_text: parsedResponse.proposed_text,
      position: parsedResponse.position || 'конец',
      reasoning: parsedResponse.reasoning || '',
      tokens_used: tokensUsed,
    };
  } catch (e) {
    // Fallback if response is not valid JSON
    return {
      proposed_text: response,
      position: 'конец',
      reasoning: 'Автоматическая правка',
      tokens_used: tokensUsed,
    };
  }
}

/**
 * Submit edit to Text Service
 */
async function submitEdit(edit) {
  const response = await axios.post(
    `${config.textServiceUrl}/api/edits`,
    {
      agent_id: config.agentId,
      proposed_text: edit.proposed_text,
      position: edit.position,
      tokens_used: edit.tokens_used,
    },
    {
      headers: {
        'Authorization': `Bearer ${config.apiToken}`,
        'Content-Type': 'application/json',
      },
    }
  );
  return response.data;
}

/**
 * Post message to chat
 */
async function postChatMessage(message) {
  const response = await axios.post(
    `${config.chatServiceUrl}/api/chat/messages`,
    {
      agent_id: config.agentId,
      message: message,
    },
    {
      headers: {
        'Authorization': `Bearer ${config.apiToken}`,
        'Content-Type': 'application/json',
      },
    }
  );
  return response.data;
}

/**
 * Main agent cycle with retry logic
 */
async function agentCycle() {
  let retries = 0;

  while (isRunning && retries < config.maxRetries) {
    try {
      // Step 1: Get current document
      console.log(`[${config.agentId}] Fetching current document...`);
      const document = await getCurrentDocument();
      console.log(`[${config.agentId}] Document version: ${document.version}`);

      // Step 2: Read chat messages
      console.log(`[${config.agentId}] Reading chat messages...`);
      const chatMessages = await getChatMessages();
      if (chatMessages.length > 0) {
        console.log(`[${config.agentId}] Found ${chatMessages.length} new messages`);
      }

      // Step 3: Generate edit via OpenAI
      console.log(`[${config.agentId}] Generating edit proposal...`);
      const edit = await generateEdit(document.text, chatMessages);
      console.log(`[${config.agentId}] Generated edit (${edit.tokens_used} tokens used)`);

      // Step 4: Submit edit
      console.log(`[${config.agentId}] Submitting edit...`);
      const submitResult = await submitEdit(edit);
      console.log(`[${config.agentId}] Edit ${submitResult.status}: ${submitResult.edit_id}`);

      // Step 5: Post chat message
      const chatMessage = `[${config.agentRole}] Предложил правку: ${edit.reasoning}`;
      console.log(`[${config.agentId}] Posting to chat...`);
      await postChatMessage(chatMessage);

      // Reset retry counter on success
      retries = 0;

      // Step 6: Wait before next cycle
      await sleep(config.cycleDelayMs);

    } catch (error) {
      // Handle budget exceeded (429)
      if (error.response && error.response.status === 429) {
        console.log(`[${config.agentId}] Budget exceeded (429). Shutting down gracefully.`);
        isRunning = false;
        break;
      }

      // Handle other errors with retry logic
      retries++;
      const backoffDelay = getBackoffDelay(retries);
      
      console.error(`[${config.agentId}] Error in agent cycle (attempt ${retries}/${config.maxRetries}):`, 
        error.message);
      
      if (retries < config.maxRetries) {
        console.log(`[${config.agentId}] Retrying in ${backoffDelay}ms...`);
        await sleep(backoffDelay);
      } else {
        console.error(`[${config.agentId}] Max retries reached. Shutting down.`);
        isRunning = false;
      }
    }
  }
}

/**
 * Graceful shutdown handler
 */
function setupGracefulShutdown() {
  const shutdown = async (signal) => {
    console.log(`\n[${config.agentId}] Received ${signal}. Shutting down gracefully...`);
    isRunning = false;
    
    // Give time for current cycle to complete
    await sleep(2000);
    
    console.log(`[${config.agentId}] Shutdown complete.`);
    process.exit(0);
  };

  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));
}

/**
 * Main entry point
 */
async function main() {
  // Validate configuration
  if (!config.openaiApiKey) {
    console.error('ERROR: OPENAI_API_KEY is required');
    process.exit(1);
  }

  setupGracefulShutdown();

  console.log(`[${config.agentId}] Starting agent cycle...`);
  console.log(`[${config.agentId}] Role: ${config.agentRole}`);
  
  try {
    await agentCycle();
  } catch (error) {
    console.error(`[${config.agentId}] Fatal error:`, error);
    process.exit(1);
  }

  console.log(`[${config.agentId}] Agent cycle completed.`);
}

// Start the agent
main();
