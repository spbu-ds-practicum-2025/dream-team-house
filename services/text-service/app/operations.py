"""
Core business logic for text operations
Based on multi_agent_editor_demo_Version2.py
"""
from typing import Optional, Tuple
from app.schemas import EditRequest

# Text length limits
MAX_NEW_TEXT_LENGTH = 10000
MAX_ANCHOR_LENGTH = 5000
MAX_OLD_TEXT_LENGTH = 5000


def apply_operation_to_text(text: str, edit: EditRequest) -> Tuple[str, bool]:
    """
    Apply edit operation to text using anchor-based positioning.
    Returns (new_text, success)
    
    This follows the logic from multi_agent_editor_demo_Version2.py:
    - All operations use text anchors, not indices
    - If fragment not found, operation fails
    """
    operation = edit.operation.lower()
    
    if operation == "none":
        return text, False
    
    def find_target() -> Optional[str]:
        """Find the target text to operate on"""
        if edit.old_text and edit.old_text.strip():
            return edit.old_text
        if edit.anchor and edit.anchor.strip():
            return edit.anchor
        return None
    
    if operation == "insert":
        # Insert new_text before or after anchor
        if not edit.anchor or not edit.new_text or not edit.position:
            return text, False
        
        idx = text.find(edit.anchor)
        if idx == -1:
            return text, False
        
        if edit.position == "before":
            insert_pos = idx
        elif edit.position == "after":
            insert_pos = idx + len(edit.anchor)
        else:
            return text, False
        
        new_text = text[:insert_pos] + edit.new_text + text[insert_pos:]
        return new_text, True
    
    elif operation == "replace":
        # Replace old_text with new_text
        target = find_target()
        if not target or not edit.new_text:
            return text, False
        
        idx = text.find(target)
        if idx == -1:
            return text, False
        
        new_text = text[:idx] + edit.new_text + text[idx + len(target):]
        return new_text, True
    
    elif operation == "delete":
        # Delete target text
        target = find_target()
        if not target:
            return text, False
        
        idx = text.find(target)
        if idx == -1:
            return text, False
        
        new_text = text[:idx] + text[idx + len(target):]
        return new_text, True
    
    return text, False


def validate_edit_request(edit: EditRequest) -> Tuple[bool, Optional[str]]:
    """
    Validate edit request
    Returns (is_valid, error_message)
    """
    operation = edit.operation.lower()
    
    if operation not in ["insert", "replace", "delete", "none"]:
        return False, f"Invalid operation: {operation}"
    
    if operation == "none":
        return False, "Operation 'none' not allowed"
    
    if operation == "insert":
        if not edit.anchor:
            return False, "Insert operation requires anchor"
        if not edit.new_text:
            return False, "Insert operation requires new_text"
        if not edit.position or edit.position not in ["before", "after"]:
            return False, "Insert operation requires position (before/after)"
    
    elif operation == "replace":
        if not (edit.anchor or edit.old_text):
            return False, "Replace operation requires anchor or old_text"
        if not edit.new_text:
            return False, "Replace operation requires new_text"
    
    elif operation == "delete":
        if not (edit.anchor or edit.old_text):
            return False, "Delete operation requires anchor or old_text"
    
    # Check text length limits
    if edit.new_text and len(edit.new_text) > MAX_NEW_TEXT_LENGTH:
        return False, f"new_text exceeds {MAX_NEW_TEXT_LENGTH} character limit"
    
    if edit.anchor and len(edit.anchor) > MAX_ANCHOR_LENGTH:
        return False, f"anchor exceeds {MAX_ANCHOR_LENGTH} character limit"
    
    if edit.old_text and len(edit.old_text) > MAX_OLD_TEXT_LENGTH:
        return False, f"old_text exceeds {MAX_OLD_TEXT_LENGTH} character limit"
    
    return True, None
