"""
Unit tests for Chat Service
"""
import pytest
from app.schemas import ChatMessageRequest, EditIntent, EditComment, IntentStatus, CommentKind, OperationType


class TestChatSchemas:
    """Test Chat Service schemas"""
    
    def test_chat_message_request_simple(self):
        """Test simple message request"""
        request = ChatMessageRequest(
            agent_id="agent-01",
            message="Working on introduction section",
        )
        
        assert request.agent_id == "agent-01"
        assert request.message == "Working on introduction section"
        assert request.intent is None
        assert request.comment is None
        assert request.document_id is None
    
    def test_chat_message_with_intent(self):
        """Test message with intent"""
        intent = EditIntent(
            intent_id="intent-001",
            agent_id="agent-01",
            operation=OperationType.REPLACE,
            anchor="old text",
            summary="Replace old text with new",
            status=IntentStatus.PROPOSED,
            created_at=1234567890.0,
        )
        
        request = ChatMessageRequest(
            agent_id="agent-01",
            message="Proposing to replace text",
            intent=intent,
            document_id="doc-1",
        )
        
        assert request.intent is not None
        assert request.intent.intent_id == "intent-001"
        assert request.intent.operation == OperationType.REPLACE
        assert request.document_id == "doc-1"
    
    def test_chat_message_with_comment(self):
        """Test message with comment"""
        comment = EditComment(
            comment_id="comment-001",
            target_intent_id="intent-001",
            agent_id="agent-02",
            kind=CommentKind.SUPPORT,
            content="I agree with this change",
            created_at=1234567890.0,
        )
        
        request = ChatMessageRequest(
            agent_id="agent-02",
            message="Supporting the change",
            comment=comment,
        )
        
        assert request.comment is not None
        assert request.comment.comment_id == "comment-001"
        assert request.comment.kind == CommentKind.SUPPORT
    
    def test_intent_status_values(self):
        """Test intent status enum"""
        assert IntentStatus.PROPOSED.value == "proposed"
        assert IntentStatus.CONFIRMED.value == "confirmed"
        assert IntentStatus.CANCELLED.value == "cancelled"
        assert IntentStatus.EXECUTED.value == "executed"
    
    def test_comment_kind_values(self):
        """Test comment kind enum"""
        assert CommentKind.CRITIQUE.value == "critique"
        assert CommentKind.SUPPORT.value == "support"
        assert CommentKind.SUGGESTION.value == "suggestion"
    
    def test_operation_type_values(self):
        """Test operation type enum"""
        assert OperationType.INSERT.value == "insert"
        assert OperationType.REPLACE.value == "replace"
        assert OperationType.DELETE.value == "delete"
        assert OperationType.NONE.value == "none"
