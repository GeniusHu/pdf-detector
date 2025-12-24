#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket service for real-time progress updates
All WebSocket messages use camelCase to match frontend expectations
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.logger = logging.getLogger(__name__)

    async def connect(self, websocket: WebSocket, task_id: str):
        """Accept WebSocket connection for a specific task"""
        await websocket.accept()

        if task_id not in self.active_connections:
            self.active_connections[task_id] = []

        self.active_connections[task_id].append(websocket)
        self.logger.info(f"WebSocket connected for task {task_id}. Total connections: {len(self.active_connections[task_id])}")

    def disconnect(self, websocket: WebSocket, task_id: str):
        """Remove WebSocket connection"""
        if task_id in self.active_connections:
            try:
                self.active_connections[task_id].remove(websocket)
                self.logger.info(f"WebSocket disconnected for task {task_id}. Remaining connections: {len(self.active_connections[task_id])}")

                # Clean up empty task connections
                if not self.active_connections[task_id]:
                    del self.active_connections[task_id]

            except ValueError:
                # Connection was already removed
                pass

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to a specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            self.logger.error(f"Error sending personal message: {str(e)}")

    async def broadcast_to_task(self, task_id: str, data: Dict[str, Any]):
        """Broadcast message to all connections for a specific task"""
        if task_id in self.active_connections:
            message = {
                "type": data.get("type", "update"),
                "taskId": task_id,
                "data": data,
                "timestamp": asyncio.get_event_loop().time()
            }

            # Convert to JSON string
            json_message = json.dumps(message, default=str)

            # Send to all connections for this task
            disconnected_connections = []
            for connection in self.active_connections[task_id]:
                try:
                    await connection.send_text(json_message)
                except Exception as e:
                    self.logger.warning(f"Error broadcasting to connection: {str(e)}")
                    disconnected_connections.append(connection)

            # Remove disconnected connections
            for connection in disconnected_connections:
                self.disconnect(connection, task_id)

    async def broadcast_progress(
        self,
        task_id: str,
        progress: float,
        message: str,
        current_step: str = "",
        estimated_remaining: Optional[int] = None
    ):
        """Send progress update to all connections for a task"""

        data = {
            "type": "progress",
            "progress": progress,
            "message": message,
            "currentStep": current_step,
            "estimatedRemainingSeconds": estimated_remaining
        }

        await self.broadcast_to_task(task_id, data)

    async def broadcast_completed(self, task_id: str, result_data: Dict[str, Any]):
        """Send completion message to all connections for a task"""

        data = {
            "type": "completed",
            "message": "Processing completed successfully!",
            "result": result_data
        }

        await self.broadcast_to_task(task_id, data)

    async def broadcast_error(self, task_id: str, error_message: str, error_details: Optional[Dict] = None):
        """Send error message to all connections for a task"""

        data = {
            "type": "error",
            "message": error_message,
            "errorDetails": error_details
        }

        await self.broadcast_to_task(task_id, data)

    async def broadcast_cancelled(self, task_id: str):
        """Send cancellation message to all connections for a task"""

        data = {
            "type": "cancelled",
            "message": "Task was cancelled"
        }

        await self.broadcast_to_task(task_id, data)

    def get_active_tasks(self) -> List[str]:
        """Get list of tasks with active connections"""
        return list(self.active_connections.keys())

    def get_connection_count(self, task_id: str) -> int:
        """Get number of active connections for a task"""
        return len(self.active_connections.get(task_id, []))

    def get_total_connections(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())

    async def close_all_connections(self):
        """Close all active WebSocket connections"""
        for task_id, connections in list(self.active_connections.items()):
            for connection in connections:
                try:
                    await connection.close()
                except Exception as e:
                    self.logger.warning(f"Error closing connection: {str(e)}")

        self.active_connections.clear()
        self.logger.info("All WebSocket connections closed")


class WebSocketManager:
    """Enhanced WebSocket manager with additional features"""

    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.logger = logging.getLogger(__name__)

    async def connect(self, websocket: WebSocket, task_id: str):
        """Connect a new WebSocket"""
        await self.connection_manager.connect(websocket, task_id)

    def disconnect(self, websocket: WebSocket, task_id: str):
        """Disconnect a WebSocket"""
        self.connection_manager.disconnect(websocket, task_id)

    async def send_progress_update(
        self,
        task_id: str,
        progress: float,
        message: str,
        current_step: str = "",
        estimated_remaining: Optional[int] = None,
        details: Optional[Dict] = None
    ):
        """Send progress update with enhanced details"""

        data = {
            "type": "progress",
            "progress": progress,
            "message": message,
            "currentStep": current_step,
            "estimatedRemainingSeconds": estimated_remaining,
            "details": details or {}
        }

        await self.connection_manager.broadcast_to_task(task_id, data)

    async def send_task_status(self, task_id: str, status: str, message: str):
        """Send task status update"""

        data = {
            "type": "status",
            "status": status,
            "message": message
        }

        await self.connection_manager.broadcast_to_task(task_id, data)

    async def send_result_update(self, task_id: str, partial_results: Dict[str, Any]):
        """Send partial results update"""

        data = {
            "type": "results_update",
            "partialResults": partial_results
        }

        await self.connection_manager.broadcast_to_task(task_id, data)

    async def send_file_processing_update(
        self,
        task_id: str,
        file_number: int,
        file_name: str,
        progress: float,
        current_operation: str
    ):
        """Send file-specific processing update"""

        data = {
            "type": "file_processing",
            "fileNumber": file_number,
            "fileName": file_name,
            "progress": progress,
            "currentOperation": current_operation
        }

        await self.connection_manager.broadcast_to_task(task_id, data)

    async def send_similarity_update(
        self,
        task_id: str,
        sequences_analyzed: int,
        total_sequences: int,
        similar_found: int,
        current_similarity_range: str
    ):
        """Send similarity detection progress update"""

        data = {
            "type": "similarity_progress",
            "sequencesAnalyzed": sequences_analyzed,
            "totalSequences": total_sequences,
            "similarFound": similar_found,
            "currentSimilarityRange": current_similarity_range,
            "progressPercentage": (sequences_analyzed / total_sequences) if total_sequences > 0 else 0
        }

        await self.connection_manager.broadcast_to_task(task_id, data)

    async def send_export_progress(
        self,
        task_id: str,
        export_format: str,
        progress: float,
        current_file: str
    ):
        """Send export generation progress update"""

        data = {
            "type": "export_progress",
            "exportFormat": export_format,
            "progress": progress,
            "currentFile": current_file
        }

        await self.connection_manager.broadcast_to_task(task_id, data)

    async def send_completion_notification(
        self,
        task_id: str,
        result_summary: Dict[str, Any],
        export_files: Dict[str, str]
    ):
        """Send task completion notification with summary"""

        data = {
            "type": "completed",
            "message": "PDF similarity detection completed successfully!",
            "resultSummary": result_summary,
            "exportFiles": export_files
        }

        await self.connection_manager.broadcast_to_task(task_id, data)

    async def send_error_notification(
        self,
        task_id: str,
        error_type: str,
        error_message: str,
        error_details: Optional[Dict] = None,
        recovery_suggestions: Optional[List[str]] = None
    ):
        """Send detailed error notification"""

        data = {
            "type": "error",
            "errorType": error_type,
            "message": error_message,
            "errorDetails": error_details,
            "recoverySuggestions": recovery_suggestions or []
        }

        await self.connection_manager.broadcast_to_task(task_id, data)

    def get_statistics(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics"""

        return {
            "totalConnections": self.connection_manager.get_total_connections(),
            "activeTasks": len(self.connection_manager.get_active_tasks()),
            "tasksWithConnections": {
                task_id: self.connection_manager.get_connection_count(task_id)
                for task_id in self.connection_manager.get_active_tasks()
            }
        }

    async def cleanup_task_connections(self, task_id: str):
        """Clean up all connections for a specific task"""
        if task_id in self.connection_manager.active_connections:
            connections = self.connection_manager.active_connections[task_id].copy()
            for connection in connections:
                try:
                    await connection.close()
                except Exception as e:
                    self.logger.warning(f"Error closing connection for task {task_id}: {str(e)}")

            del self.connection_manager.active_connections[task_id]
            self.logger.info(f"Cleaned up all connections for task {task_id}")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
