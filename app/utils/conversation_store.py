"""
File-based conversation storage for HeliosCommand.

Stores conversation history in JSON files within the data/conversations directory.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


STORAGE_DIR = Path(__file__).parent.parent.parent / "data" / "conversations"


class ConversationStore:
    """File-based storage for conversation history."""

    def __init__(self, storage_dir: Optional[Path] = None) -> None:
        self.storage_dir = storage_dir or STORAGE_DIR
        self._ensure_storage_dir()

    def _ensure_storage_dir(self) -> None:
        """Create storage directory if it doesn't exist."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        gitkeep = self.storage_dir / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

    def _get_conversation_path(self, conversation_id: str) -> Path:
        """Get the file path for a conversation."""
        safe_id = conversation_id.replace("/", "_").replace("\\", "_")
        return self.storage_dir / f"{safe_id}.json"

    def save_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Save conversation to file.

        Args:
            conversation_id: Unique identifier for the conversation
            messages: List of message dictionaries
            metadata: Optional metadata (intent, location, etc.)
        """
        file_path = self._get_conversation_path(conversation_id)

        data = {
            "conversation_id": conversation_id,
            "updated_at": datetime.now().isoformat(),
            "messages": messages,
            "metadata": metadata or {},
        }

        if file_path.exists():
            try:
                with open(file_path, "r") as f:
                    existing = json.load(f)
                    data["created_at"] = existing.get("created_at", data["updated_at"])
            except (json.JSONDecodeError, KeyError):
                data["created_at"] = data["updated_at"]
        else:
            data["created_at"] = data["updated_at"]

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def load_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Load conversation from file.

        Args:
            conversation_id: Unique identifier for the conversation

        Returns:
            Conversation data or None if not found
        """
        file_path = self._get_conversation_path(conversation_id)

        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            return data
        except (json.JSONDecodeError, IOError):
            return None

    def get_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get just the messages from a conversation.

        Args:
            conversation_id: Unique identifier for the conversation

        Returns:
            List of messages or empty list if not found
        """
        data = self.load_conversation(conversation_id)
        if data:
            return data.get("messages", [])
        return []

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a single message to a conversation.

        Args:
            conversation_id: Unique identifier for the conversation
            role: Message role ('user' or 'assistant')
            content: Message content
            metadata: Optional message metadata
        """
        messages = self.get_messages(conversation_id)

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        if metadata:
            message["metadata"] = metadata

        messages.append(message)

        existing_data = self.load_conversation(conversation_id)
        conv_metadata = existing_data.get("metadata", {}) if existing_data else {}

        self.save_conversation(conversation_id, messages, conv_metadata)

    def update_metadata(
        self,
        conversation_id: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Update conversation metadata.

        Args:
            conversation_id: Unique identifier for the conversation
            metadata: Metadata to update (merged with existing)
        """
        existing = self.load_conversation(conversation_id)
        if existing:
            existing_metadata = existing.get("metadata", {})
            existing_metadata.update(metadata)
            self.save_conversation(
                conversation_id,
                existing.get("messages", []),
                existing_metadata,
            )
        else:
            self.save_conversation(conversation_id, [], metadata)

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation file.

        Args:
            conversation_id: Unique identifier for the conversation

        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_conversation_path(conversation_id)

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_conversations(self) -> List[Dict[str, Any]]:
        """List all conversations with basic info.

        Returns:
            List of conversation summaries
        """
        conversations = []

        for file_path in self.storage_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    conversations.append({
                        "conversation_id": data.get("conversation_id"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "message_count": len(data.get("messages", [])),
                    })
            except (json.JSONDecodeError, IOError):
                continue

        conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return conversations

    def clear_all(self) -> int:
        """Delete all conversation files.

        Returns:
            Number of conversations deleted
        """
        count = 0
        for file_path in self.storage_dir.glob("*.json"):
            file_path.unlink()
            count += 1

        return count


_store: Optional[ConversationStore] = None


def get_conversation_store() -> ConversationStore:
    """Get the global conversation store instance."""
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
