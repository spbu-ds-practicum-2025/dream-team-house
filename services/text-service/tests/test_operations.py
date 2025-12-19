"""
Unit tests for text operations
"""
import pytest
from app.operations import apply_operation_to_text, validate_edit_request, build_diff_segments
from app.schemas import EditRequest


class TestApplyOperationToText:
    """Test apply_operation_to_text function"""
    
    def test_insert_before(self):
        """Test insert operation before anchor"""
        text = "Hello world"
        edit = EditRequest(
            agent_id="test",
            operation="insert",
            anchor="world",
            position="before",
            new_text="beautiful ",
            tokens_used=0
        )
        
        new_text, success = apply_operation_to_text(text, edit)
        assert success is True
        assert new_text == "Hello beautiful world"
    
    def test_insert_after(self):
        """Test insert operation after anchor"""
        text = "Hello world"
        edit = EditRequest(
            agent_id="test",
            operation="insert",
            anchor="Hello",
            position="after",
            new_text=" there",
            tokens_used=0
        )
        
        new_text, success = apply_operation_to_text(text, edit)
        assert success is True
        assert new_text == "Hello there world"
    
    def test_replace_with_anchor(self):
        """Test replace operation using anchor"""
        text = "Hello old world"
        edit = EditRequest(
            agent_id="test",
            operation="replace",
            anchor="old",
            new_text="new",
            tokens_used=0
        )
        
        new_text, success = apply_operation_to_text(text, edit)
        assert success is True
        assert new_text == "Hello new world"
    
    def test_replace_with_old_text(self):
        """Test replace operation using old_text"""
        text = "The quick brown fox"
        edit = EditRequest(
            agent_id="test",
            operation="replace",
            old_text="quick brown",
            new_text="slow red",
            tokens_used=0
        )
        
        new_text, success = apply_operation_to_text(text, edit)
        assert success is True
        assert new_text == "The slow red fox"
    
    def test_delete_with_anchor(self):
        """Test delete operation using anchor"""
        text = "Hello beautiful world"
        edit = EditRequest(
            agent_id="test",
            operation="delete",
            anchor="beautiful ",
            tokens_used=0
        )
        
        new_text, success = apply_operation_to_text(text, edit)
        assert success is True
        assert new_text == "Hello world"
    
    def test_delete_with_old_text(self):
        """Test delete operation using old_text"""
        text = "This is a test document"
        edit = EditRequest(
            agent_id="test",
            operation="delete",
            old_text=" test",
            tokens_used=0
        )
        
        new_text, success = apply_operation_to_text(text, edit)
        assert success is True
        assert new_text == "This is a document"
    
    def test_anchor_not_found(self):
        """Test operation fails when anchor not found"""
        text = "Hello world"
        edit = EditRequest(
            agent_id="test",
            operation="replace",
            anchor="nonexistent",
            new_text="replacement",
            tokens_used=0
        )
        
        new_text, success = apply_operation_to_text(text, edit)
        assert success is False
        assert new_text == text
    
    def test_none_operation(self):
        """Test none operation returns False"""
        text = "Hello world"
        edit = EditRequest(
            agent_id="test",
            operation="none",
            tokens_used=0
        )
        
        new_text, success = apply_operation_to_text(text, edit)
        assert success is False


class TestValidateEditRequest:
    """Test validate_edit_request function"""
    
    def test_valid_insert(self):
        """Test valid insert request"""
        edit = EditRequest(
            agent_id="test",
            operation="insert",
            anchor="world",
            position="before",
            new_text="hello ",
            tokens_used=10
        )
        
        is_valid, error = validate_edit_request(edit)
        assert is_valid is True
        assert error is None
    
    def test_valid_replace(self):
        """Test valid replace request"""
        edit = EditRequest(
            agent_id="test",
            operation="replace",
            anchor="old",
            new_text="new",
            tokens_used=10
        )
        
        is_valid, error = validate_edit_request(edit)
        assert is_valid is True
        assert error is None
    
    def test_valid_delete(self):
        """Test valid delete request"""
        edit = EditRequest(
            agent_id="test",
            operation="delete",
            anchor="remove this",
            tokens_used=10
        )
        
        is_valid, error = validate_edit_request(edit)
        assert is_valid is True
        assert error is None
    
    def test_invalid_operation(self):
        """Test invalid operation type"""
        edit = EditRequest(
            agent_id="test",
            operation="invalid_op",
            tokens_used=10
        )
        
        is_valid, error = validate_edit_request(edit)
        assert is_valid is False
        assert "Invalid operation" in error
    
    def test_none_operation_not_allowed(self):
        """Test none operation is not allowed"""
        edit = EditRequest(
            agent_id="test",
            operation="none",
            tokens_used=10
        )
        
        is_valid, error = validate_edit_request(edit)
        assert is_valid is False
        assert "not allowed" in error
    
    def test_insert_missing_anchor(self):
        """Test insert without anchor"""
        edit = EditRequest(
            agent_id="test",
            operation="insert",
            position="before",
            new_text="text",
            tokens_used=10
        )
        
        is_valid, error = validate_edit_request(edit)
        assert is_valid is False
        assert "requires anchor" in error
    
    def test_insert_missing_position(self):
        """Test insert without position"""
        edit = EditRequest(
            agent_id="test",
            operation="insert",
            anchor="world",
            new_text="text",
            tokens_used=10
        )
        
        is_valid, error = validate_edit_request(edit)
        assert is_valid is False
        assert "requires position" in error
    
    def test_replace_missing_target(self):
        """Test replace without anchor or old_text"""
        edit = EditRequest(
            agent_id="test",
            operation="replace",
            new_text="text",
            tokens_used=10
        )
        
        is_valid, error = validate_edit_request(edit)
        assert is_valid is False
        assert "requires anchor or old_text" in error
    
    def test_text_length_limit(self):
        """Test text length limits"""
        edit = EditRequest(
            agent_id="test",
            operation="replace",
            anchor="old",
            new_text="x" * 10001,  # Exceeds limit
            tokens_used=10
        )
        
        is_valid, error = validate_edit_request(edit)
        assert is_valid is False
        assert "exceeds" in error


class TestBuildDiffSegments:
    """Tests for diff segment builder"""

    def test_diff_insert_and_replace(self):
        old = "Hello world"
        new = "Hello brave new world"
        segments = build_diff_segments(old, new)

        # Should keep greeting, add brave and new
        assert {"type": "equal", "text": "Hello"} in segments
        assert {"type": "insert", "text": "brave new"} in segments

    def test_diff_replace_marks_delete_and_replace(self):
        old = "Old text here"
        new = "New text here"
        segments = build_diff_segments(old, new)

        assert {"type": "delete", "text": "Old"} in segments
        assert {"type": "replace", "text": "New"} in segments
