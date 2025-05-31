import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass, asdict
from enum import Enum

class OperationType(Enum):
    FETCH = "fetch"
    PARSE = "parse"
    DELETE = "delete"
    RENAME = "rename"
    SAVE = "save"
    CLEAR = "clear"
    ERROR = "error"

@dataclass
class Step:
    operation: OperationType
    details: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation.value,
            "details": self.details,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Step':
        return cls(
            operation=OperationType(data["operation"]),
            details=data["details"],
            timestamp=data["timestamp"],
            metadata=data.get("metadata")
        )

class StepHistory:
    def __init__(self, storage_path: Optional[str] = None):
        self.steps: List[Step] = []
        self.storage_path = storage_path
        # Start with empty steps list for each new session
        # Previous steps are not loaded

    def _load_steps(self) -> None:
        """Load steps from storage if available"""
        if not self.storage_path or not os.path.exists(self.storage_path):
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                self.steps = [Step.from_dict(step_data) for step_data in data]
        except Exception as e:
            logging.error(f"Error loading steps from storage: {str(e)}")
            self.steps = []

    def _save_steps(self) -> None:
        """Save steps to storage if path is configured"""
        if not self.storage_path:
            return

        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump([step.to_dict() for step in self.steps], f)
        except Exception as e:
            logging.error(f"Error saving steps to storage: {str(e)}")

    def add_step(self, operation: OperationType, details: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a new step to the history"""
        if not isinstance(operation, OperationType):
            raise ValueError(f"Invalid operation type: {operation}")

        step = Step(
            operation=operation,
            details=details,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            metadata=metadata
        )
        self.steps.append(step)
        self._save_steps()

    def get_steps(self, 
                 operation_type: Optional[OperationType] = None,
                 start_time: Optional[str] = None,
                 end_time: Optional[str] = None) -> List[Step]:
        """Get filtered steps based on criteria"""
        filtered_steps = self.steps

        if operation_type:
            filtered_steps = [s for s in filtered_steps if s.operation == operation_type]

        if start_time:
            filtered_steps = [s for s in filtered_steps if s.timestamp >= start_time]

        if end_time:
            filtered_steps = [s for s in filtered_steps if s.timestamp <= end_time]

        return filtered_steps

    def clear_steps(self) -> None:
        """Clear all steps"""
        self.steps = []
        self._save_steps()

    def get_last_step(self) -> Optional[Step]:
        """Get the most recent step"""
        return self.steps[-1] if self.steps else None

    def get_step_count(self) -> int:
        """Get total number of steps"""
        return len(self.steps)

    def get_operation_count(self, operation_type: OperationType) -> int:
        """Get count of steps for a specific operation type"""
        return len([s for s in self.steps if s.operation == operation_type]) 