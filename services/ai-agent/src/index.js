/**
 * AI Agent - Distributed document editing agent
 * Based on multi_agent_editor_demo_Version2.py
 * 
 * Implements simplified but functional agent cycle:
 * 1. Get document from Text Service
 * 2. Read chat messages
 * 3. Generate edit via OpenAI API
 * 4. Submit edit to Text Service
 * 5. Post chat message
 * 6. Wait and repeat
 */

import axios from 'axios';
import OpenAI from 'openai';

// Configuration from environment
const AGENT_ROLE = process.env.AGENT_ROLE || 'general editor';
const API_TOKEN = process.env.API_TOKEN || 'test-token-123';
const TEXT_SERVICE_URL = process.env.TEXT_SERVICE_URL || 'http://localhost';
const CHAT_SERVICE_URL = process.env.CHAT_SERVICE_URL || 'http://localhost';
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const OPENAI_BASE_URL = process.env.OPENAI_BASE_URL || 'https://api.proxyapi.ru/openai/v1';

// Generate secure agent ID
const AGENT_ID = `agent-${Date.now()}-${Math.random().toString(36).substring(7)}`;
const TARGET_DOCUMENT_ID = process.env.DOCUMENT_ID || null;
const CONFIGURED_MAX_EDITS = parseInt(process.env.MAX_EDITS || '1');
const CYCLE_DELAY_MS = parseInt(process.env.CYCLE_DELAY_MS || '2000');
const MAX_RETRIES = 5;
const DEFAULT_EXPANSION_PROMPT = 'Увеличивай объем текста, добавляя ценность, новые детали, примеры и связующие переходы без пустых повторов.';

console.log('AI Agent starting...');
console.log('Configuration:', {
  agentId: AGENT_ID,
  agentRole: AGENT_ROLE,
  textServiceUrl: TEXT_SERVICE_URL,
  chatServiceUrl: CHAT_SERVICE_URL,
  documentId: TARGET_DOCUMENT_ID,
  maxEdits: CONFIGURED_MAX_EDITS,
  cycleDelay: CYCLE_DELAY_MS,
  hasOpenAiKey: !!OPENAI_API_KEY
});

// Initialize OpenAI client
const openai = new OpenAI({
  apiKey: OPENAI_API_KEY,
  baseURL: OPENAI_BASE_URL,
});

// Agent state
let completedEdits = 0;
let lastChatTimestamp = null;
let isRunning = true;
let maxEditsAllowed = CONFIGURED_MAX_EDITS;
let activeRoleName = AGENT_ROLE;
let activeRolePrompt = '';
let agentRolesFromDocument = [];

// Retry with exponential backoff
async function retryWithBackoff(fn, retries = MAX_RETRIES) {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === retries - 1) throw error;
      
      const delay = Math.min(1000 * Math.pow(2, i), 10000);
      console.log(`[${AGENT_ID}] Retry ${i + 1}/${retries} after ${delay}ms...`);
      await sleep(delay);
    }
  }
}

// Sleep helper
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function hashString(input) {
  return input.split('').reduce((acc, char) => (acc * 31 + char.charCodeAt(0)) >>> 0, 7);
}

function selectAgentRole(agentRoles = []) {
  if (!agentRoles.length) return null;
  const index = hashString(AGENT_ID) % agentRoles.length;
  return agentRoles[index];
}

// Get current document
async function getCurrentDocument() {
  const response = await retryWithBackoff(async () => {
    const params = {};
    if (TARGET_DOCUMENT_ID) {
      params.document_id = TARGET_DOCUMENT_ID;
    }
    return await axios.get(`${TEXT_SERVICE_URL}/api/document/current`, {
      headers: { 'Authorization': `Bearer ${API_TOKEN}` },
      params,
    });
  });
  return response.data;
}

// Get chat messages
async function getChatMessages(since = null) {
  const params = {};
  if (since) params.since = since;
  if (TARGET_DOCUMENT_ID) params.document_id = TARGET_DOCUMENT_ID;
  
  const response = await retryWithBackoff(async () => {
    return await axios.get(`${CHAT_SERVICE_URL}/api/chat/messages`, {
      params,
      headers: { 'Authorization': `Bearer ${API_TOKEN}` }
    });
  });
  return response.data;
}

// Post chat message
async function postChatMessage(message, intent = null, comment = null, role = activeRoleName) {
  const data = {
    agent_id: AGENT_ID,
    message,
  };
  if (TARGET_DOCUMENT_ID) {
    data.document_id = TARGET_DOCUMENT_ID;
  }
  if (role) {
    data.agent_role = role;
  }
  
  if (intent) data.intent = intent;
  if (comment) data.comment = comment;
  
  await retryWithBackoff(async () => {
    return await axios.post(`${CHAT_SERVICE_URL}/api/chat/messages`, data, {
      headers: { 'Authorization': `Bearer ${API_TOKEN}` }
    });
  });
}

// Submit edit
async function submitEdit(operation, anchor, position, oldText, newText, tokensUsed) {
  const data = {
    document_id: TARGET_DOCUMENT_ID,
    agent_id: AGENT_ID,
    operation,
    anchor,
    position,
    old_text: oldText,
    new_text: newText,
    tokens_used: tokensUsed,
  };
  
  const response = await retryWithBackoff(async () => {
    return await axios.post(`${TEXT_SERVICE_URL}/api/edits`, data, {
      headers: { 'Authorization': `Bearer ${API_TOKEN}` }
    });
  });
  
  return response.data;
}

// Generate edit using OpenAI
async function generateEdit(documentText, chatContext) {
  const systemPrompt = `You are an AI agent working as "${activeRoleName}".
Role focus: ${activeRolePrompt || DEFAULT_EXPANSION_PROMPT}

Return a JSON object with this structure:
{
  "operation": "insert" | "replace" | "delete",
  "anchor": "text fragment to find in document",
  "position": "before" | "after" (only for insert),
  "old_text": "text to replace/delete" (optional, can be same as anchor),
  "new_text": "new text for insert/replace",
  "reasoning": "brief explanation"
}

Rules:
- Prioritize INSERT or REPLACE that expand content with new paragraphs, facts, transitions, or applied insights.
- Keep tone professional; avoid pleading phrases or repetitive emphasis.
- Anchor must exist in the document exactly; keep changes coherent with surrounding text.
- Each edit should feel like one meaningful cycle, not scattered micro-changes.
- For INSERT: specify anchor, position (before/after), and new_text
- For REPLACE: specify anchor (or old_text), and new_text
- For DELETE: specify anchor (or old_text) and use only when removing clear redundancy.`;

  const userPrompt = `Current document:\n${documentText}\n\nRecent chat:\n${chatContext}\n\nPropose one coherent improvement that meaningfully expands the text (more details, examples, bridges). Avoid filler or repeating pleas.`;

  try {
    const response = await openai.chat.completions.create({
      model: 'gpt-4o-mini',
      messages: [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ],
      response_format: { type: 'json_object' },
      temperature: 0.7,
      max_tokens: 5000,
    });

    const content = response.choices[0].message.content;
    const tokensUsed = response.usage.total_tokens;
    
    const edit = JSON.parse(content);
    edit.tokens_used = tokensUsed;
    
    return edit;
  } catch (error) {
    console.error(`[${AGENT_ID}] OpenAI API error:`, error.message);
    throw error;
  }
}

// Build chat summary
function buildChatSummary(messages, maxMessages = 20) {
  const recent = messages.slice(-maxMessages);
  if (recent.length === 0) return '(no messages)';
  
  return recent.map(m => {
    const roleLabel = m.agent_role ? `[${m.agent_role}] ` : '';
    return `${roleLabel}${m.agent_id}: ${m.message}`;
  }).join('\n');
}

// Main agent cycle
async function agentCycle() {
  try {
    console.log(`\n[${AGENT_ID}] === Starting edit cycle ${completedEdits + 1}/${maxEditsAllowed} ===`);
    
    // Step 1-2: Get document and chat
    console.log(`[${AGENT_ID}] Fetching document and chat...`);
    let document;
    try {
      document = await getCurrentDocument();
    } catch (error) {
      if (error.response?.status === 404) {
        console.log(`[${AGENT_ID}] No document found, waiting...`);
        return; // Wait for next cycle
      }
      throw error;
    }

    const activeDocumentId = document.document_id || TARGET_DOCUMENT_ID || 'unknown';
    if (document.status && document.status !== 'active') {
      console.log(`[${AGENT_ID}] Document ${activeDocumentId} status is ${document.status}, stopping agent`);
      isRunning = false;
      await postChatMessage(`Stopping work: document status ${document.status}`);
      return;
    }

    if (document.max_edits && document.total_versions && (document.total_versions - 1) >= document.max_edits) {
      console.log(`[${AGENT_ID}] Document ${activeDocumentId} reached max edits (${document.max_edits}), stopping agent`);
      isRunning = false;
      await postChatMessage(`Stopping work: max edits ${document.max_edits} reached`);
      return;
    }

    if (document.max_edits_per_agent) {
      maxEditsAllowed = document.max_edits_per_agent;
    }

    if (Array.isArray(document.agent_roles) && document.agent_roles.length) {
      agentRolesFromDocument = document.agent_roles;
      const selectedRole = selectAgentRole(agentRolesFromDocument);
      if (selectedRole) {
        activeRoleName = selectedRole.name || selectedRole.role_key || activeRoleName;
        activeRolePrompt = selectedRole.prompt || activeRolePrompt;
      }
    }

    if (completedEdits >= maxEditsAllowed) {
      console.log(`[${AGENT_ID}] Reached per-agent edit limit ${maxEditsAllowed}, stopping agent`);
      isRunning = false;
      await postChatMessage(`Достиг лимита правок (${maxEditsAllowed}) для роли ${activeRoleName}`);
      return;
    }
    
    const chatMessages = await getChatMessages(lastChatTimestamp);
    
    if (chatMessages.length > 0) {
      lastChatTimestamp = chatMessages[chatMessages.length - 1].timestamp;
    }
    
    const chatSummary = buildChatSummary(chatMessages);
    
    console.log(`[${AGENT_ID}] Document ${activeDocumentId} version: ${document.version}, length: ${document.text.length} chars`);
    console.log(`[${AGENT_ID}] Chat messages: ${chatMessages.length}`);
    
    // Step 3: Generate edit via OpenAI
    console.log(`[${AGENT_ID}] Generating edit...`);
    const edit = await generateEdit(document.text, chatSummary);
    
    console.log(`[${AGENT_ID}] Generated ${edit.operation}: ${edit.reasoning}`);
    
    // Validate anchor exists in document
    if (edit.anchor && !document.text.includes(edit.anchor)) {
      console.log(`[${AGENT_ID}] Warning: Anchor not found in document, skipping edit`);
      await postChatMessage(`(skipped) Generated edit but anchor not found: ${edit.reasoning}`);
      return;
    }
    
    // Step 4: Submit edit
    console.log(`[${AGENT_ID}] Submitting edit...`);
    const result = await submitEdit(
      edit.operation,
      edit.anchor,
      edit.position,
      edit.old_text,
      edit.new_text,
      edit.tokens_used || 10
    );
    
    console.log(`[${AGENT_ID}] Edit ${result.status}: ${result.edit_id}, new version: ${result.version}`);
    
    // Step 5: Post chat message
    if (result.status === 'accepted') {
      await postChatMessage(`Applied ${edit.operation}: ${edit.reasoning}`);
      completedEdits++;
    } else {
      await postChatMessage(`Edit rejected: ${edit.reasoning}`);
    }
    
  } catch (error) {
    if (error.response?.status === 429) {
      console.log(`[${AGENT_ID}] Budget exceeded (429), stopping agent`);
      isRunning = false;
      await postChatMessage('Stopping due to budget limit');
    } else {
      console.error(`[${AGENT_ID}] Error in agent cycle:`, error.message);
      // Continue running on other errors
    }
  }
}

// Main loop
async function main() {
  console.log(`[${AGENT_ID}] Agent starting with role: ${activeRoleName}`);
  
  // Wait for a document to be available before starting work
  let documentExists = false;
  let initialDocument = null;
  console.log(`[${AGENT_ID}] Waiting for document to be initialized...`);
  
  while (!documentExists && isRunning) {
    try {
      initialDocument = await getCurrentDocument();
      documentExists = true;
      console.log(`[${AGENT_ID}] Document found! Starting work...`);
    } catch (error) {
      if (error.response?.status === 404) {
        console.log(`[${AGENT_ID}] No document yet, waiting ${CYCLE_DELAY_MS}ms...`);
        await sleep(CYCLE_DELAY_MS);
      } else {
        console.log(`[${AGENT_ID}] Error checking document: ${error.message}, retrying...`);
        await sleep(CYCLE_DELAY_MS);
      }
    }
  }
  
  if (!isRunning) {
    console.log(`[${AGENT_ID}] Agent stopped before document was found.`);
    return;
  }

  if (initialDocument) {
    if (initialDocument.max_edits_per_agent) {
      maxEditsAllowed = initialDocument.max_edits_per_agent;
    }
    if (Array.isArray(initialDocument.agent_roles) && initialDocument.agent_roles.length) {
      agentRolesFromDocument = initialDocument.agent_roles;
      const selectedRole = selectAgentRole(agentRolesFromDocument);
      if (selectedRole) {
        activeRoleName = selectedRole.name || selectedRole.role_key || activeRoleName;
        activeRolePrompt = selectedRole.prompt || activeRolePrompt;
      }
    }
  }
  
  // Initial greeting - only post once document exists
  try {
    await postChatMessage(`Hello! I'm ${AGENT_ID}, role: ${activeRoleName}. Starting work...`);
  } catch (error) {
    console.error(`[${AGENT_ID}] Failed to post initial message:`, error.message);
  }
  
  // Main loop
  while (isRunning && completedEdits < maxEditsAllowed) {
    await agentCycle();
    
    if (isRunning && completedEdits < maxEditsAllowed) {
      console.log(`[${AGENT_ID}] Waiting ${CYCLE_DELAY_MS}ms before next cycle...`);
      await sleep(CYCLE_DELAY_MS);
    }
  }
  
  console.log(`[${AGENT_ID}] Agent finished. Completed edits: ${completedEdits}/${maxEditsAllowed}`);
  
  // Goodbye message
  try {
    await postChatMessage(`Finished. Completed ${completedEdits} edits as ${activeRoleName}. Goodbye!`);
  } catch (error) {
    console.error(`[${AGENT_ID}] Failed to post goodbye message:`, error.message);
  }
}

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log(`\n[${AGENT_ID}] Received SIGINT, shutting down gracefully...`);
  isRunning = false;
});

process.on('SIGTERM', () => {
  console.log(`\n[${AGENT_ID}] Received SIGTERM, shutting down gracefully...`);
  isRunning = false;
});

// Start agent
main().catch(error => {
  console.error(`[${AGENT_ID}] Fatal error:`, error);
  process.exit(1);
});
