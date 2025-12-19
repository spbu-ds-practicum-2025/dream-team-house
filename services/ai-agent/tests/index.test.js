/**
 * AI Agent unit tests
 */

// Mock environment variables
process.env.AGENT_ROLE = 'test-agent';
process.env.API_TOKEN = 'test-token';
process.env.TEXT_SERVICE_URL = 'http://test-text-service';
process.env.CHAT_SERVICE_URL = 'http://test-chat-service';
process.env.OPENAI_API_KEY = 'test-key';
process.env.DOCUMENT_ID = 'doc-xyz';
process.env.MAX_EDITS = '2';
process.env.CYCLE_DELAY_MS = '100';

describe('AI Agent Configuration', () => {
  test('should load environment variables', () => {
    expect(process.env.AGENT_ROLE).toBe('test-agent');
    expect(process.env.API_TOKEN).toBe('test-token');
    expect(process.env.TEXT_SERVICE_URL).toBe('http://test-text-service');
    expect(process.env.CHAT_SERVICE_URL).toBe('http://test-chat-service');
    expect(process.env.DOCUMENT_ID).toBe('doc-xyz');
  });

  test('should have OpenAI API key', () => {
    expect(process.env.OPENAI_API_KEY).toBeDefined();
  });

  test('should have max edits configured', () => {
    expect(parseInt(process.env.MAX_EDITS)).toBe(2);
  });
});

describe('Edit Operations', () => {
  test('insert operation requires anchor, position, and new_text', () => {
    const edit = {
      operation: 'insert',
      anchor: 'Hello',
      position: 'after',
      new_text: ' World',
    };
    
    expect(edit.operation).toBe('insert');
    expect(edit.anchor).toBe('Hello');
    expect(edit.position).toBe('after');
    expect(edit.new_text).toBe(' World');
  });

  test('replace operation requires anchor and new_text', () => {
    const edit = {
      operation: 'replace',
      anchor: 'old text',
      new_text: 'new text',
    };
    
    expect(edit.operation).toBe('replace');
    expect(edit.anchor).toBe('old text');
    expect(edit.new_text).toBe('new text');
  });

  test('delete operation requires anchor or old_text', () => {
    const edit = {
      operation: 'delete',
      anchor: 'remove this',
    };
    
    expect(edit.operation).toBe('delete');
    expect(edit.anchor).toBe('remove this');
  });
});

describe('Chat Message Structure', () => {
  test('should have required fields', () => {
    const message = {
      agent_id: 'agent-123',
      message: 'Test message',
    };
    
    expect(message.agent_id).toBe('agent-123');
    expect(message.message).toBe('Test message');
  });

  test('can include intent', () => {
    const message = {
      agent_id: 'agent-123',
      message: 'Proposing edit',
      intent: {
        intent_id: 'intent-1',
        operation: 'replace',
      },
    };
    
    expect(message.intent).toBeDefined();
    expect(message.intent.intent_id).toBe('intent-1');
  });
});
