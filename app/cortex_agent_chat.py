"""
Reusable Cortex Agent Chat Component for Streamlit

This module provides a reusable chat interface for Snowflake Cortex Agents
that can be easily integrated into any Streamlit application.

Example usage:
    from cortex_agent_chat import CortexAgentChat
    
    # Use connections.toml for credentials, specify agent in code
    chat = CortexAgentChat.from_toml_connection(
        connection_name="LSDEMO",
        database="snowflake_intelligence",
        schema="agents",
        agent="MY_AGENT"
    )
    chat.render()
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests
import sseclient
import streamlit as st

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from models import (
    ChartEventData,
    DataAgentRunRequest,
    ErrorEventData,
    Message,
    MessageContentItem,
    StatusEventData,
    TableEventData,
    TextContentItem,
    TextDeltaEventData,
    ThinkingDeltaEventData,
    ThinkingEventData,
    ToolResultEventData,
    ToolUseEventData,
)


class CortexAgentChat:
    """
    A reusable chat component for Snowflake Cortex Agents.
    
    This class encapsulates all the functionality needed to interact with
    a Cortex Agent via REST API and render the chat interface in Streamlit.
    
    Attributes:
        pat: Personal Access Token for authentication
        host: Snowflake account host
        database: Database containing the agent
        schema: Schema containing the agent
        agent: Agent name
        model: LLM model to use (default: claude-4-sonnet)
        session_key: Key for storing messages in st.session_state
    """
    
    def __init__(
        self,
        pat: str,
        host: str,
        database: str,
        schema: str,
        agent: str,
        model: str = "claude-4-sonnet",
        session_key: Optional[str] = None,
        title: Optional[str] = None,
        chat_input_placeholder: str = "What is your question?",
        verify_ssl: bool = False,
        warehouse: Optional[str] = None,
        role: Optional[str] = None,
    ):
        """
        Initialize the Cortex Agent Chat component.
        
        Args:
            pat: Personal Access Token for authentication
            host: Snowflake account host (e.g., account.snowflakecomputing.com)
            database: Database containing the agent
            schema: Schema containing the agent
            agent: Agent name
            model: LLM model to use (default: claude-4-sonnet)
            session_key: Unique key for this chat instance in session state
            title: Title to display above the chat (optional)
            chat_input_placeholder: Placeholder text for chat input
            verify_ssl: Whether to verify SSL certificates
            warehouse: Optional warehouse to use for agent API calls (uses X-Snowflake-Warehouse header)
            role: Optional role to use for agent API calls (uses X-Snowflake-Role header)
        """
        self.pat = pat
        self.host = host
        self.database = database
        self.schema = schema
        self.agent = agent
        self.model = model
        self.session_key = session_key or f"messages_{agent}"
        self.title = f"Chat with {agent}" if title is None else title
        self.chat_input_placeholder = chat_input_placeholder
        self.verify_ssl = verify_ssl
        self.warehouse = warehouse
        self.role = role
        
        # Initialize session state for this chat instance
        if self.session_key not in st.session_state:
            st.session_state[self.session_key] = []
        
        # Initialize settings for thinking expanders
        self.thinking_setting_key = f"{self.session_key}_thinking_expanded"
        if self.thinking_setting_key not in st.session_state:
            st.session_state[self.thinking_setting_key] = True  # Default: keep open
        
        # Initialize debug mode settings
        self.debug_setting_key = f"{self.session_key}_debug_mode"
        if self.debug_setting_key not in st.session_state:
            st.session_state[self.debug_setting_key] = False  # Default: off
        
        # Initialize debug events storage
        self.debug_events_key = f"{self.session_key}_debug_events"
        if self.debug_events_key not in st.session_state:
            st.session_state[self.debug_events_key] = []
    
    @classmethod
    def from_toml_connection(
        cls,
        connection_name: str,
        database: str,
        schema: str,
        agent: str,
        toml_path: str = "~/.snowflake/connections.toml",
        **kwargs
    ) -> "CortexAgentChat":
        """
        Create a CortexAgentChat instance directly from a connections.toml file.
        
        Args:
            connection_name: Name of the connection in connections.toml
            database: Database containing the agent
            schema: Schema containing the agent
            agent: Agent name
            toml_path: Path to connections.toml (default: ~/.snowflake/connections.toml)
            **kwargs: Additional arguments passed to __init__
        
        Returns:
            Configured CortexAgentChat instance
        """
        toml_path = Path(toml_path).expanduser()
        
        with open(toml_path, "rb") as f:
            connections = tomllib.load(f)
        
        conn_config = connections.get(connection_name, {})
        if not conn_config:
            raise ValueError(f"Connection '{connection_name}' not found in {toml_path}")
        
        pat = conn_config.get('password')
        account = conn_config.get('account', '')
        host = f"{account.lower()}.snowflakecomputing.com" if account else None
        
        return cls(
            pat=pat,
            host=host,
            database=database,
            schema=schema,
            agent=agent,
            **kwargs
        )
    
    def _log_debug_event(self, event_type: str, event_data: dict):
        """
        Log a debug event if debug mode is enabled.
        
        Args:
            event_type: Type of event (e.g., "error", "status", "exception")
            event_data: Event data to log
        """
        if st.session_state.get(self.debug_setting_key, False):
            from datetime import datetime
            debug_event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "data": event_data
            }
            st.session_state[self.debug_events_key].append(debug_event)
            # Keep only last 50 events to avoid memory issues
            if len(st.session_state[self.debug_events_key]) > 50:
                st.session_state[self.debug_events_key] = st.session_state[self.debug_events_key][-50:]
    
    def _strip_annotations_from_messages(self, messages: list) -> list:
        """
        Remove annotations from messages before sending to API.
        
        Annotations (like Cortex Search results) are response-only fields that
        cause deserialization errors if included in subsequent requests.
        
        Args:
            messages: List of message objects from session state
            
        Returns:
            List of cleaned Message objects without annotations
        """
        cleaned_messages = []
        annotations_found = 0
        
        for msg in messages:
            # Convert message to dictionary if it's an object
            if hasattr(msg, 'to_dict'):
                msg_dict = msg.to_dict()
            elif isinstance(msg, dict):
                msg_dict = msg.copy()
            else:
                # If we can't process it, keep as is
                cleaned_messages.append(msg)
                continue
            
            # Clean annotations from content items
            if 'content' in msg_dict and isinstance(msg_dict['content'], list):
                for content_item in msg_dict['content']:
                    if isinstance(content_item, dict) and 'annotations' in content_item:
                        if content_item['annotations']:  # Only count if not already empty
                            annotations_found += len(content_item['annotations'])
                        # Remove annotations to prevent deserialization errors
                        content_item['annotations'] = []
            
            # Reconstruct Message object from cleaned dictionary
            # This ensures DataAgentRunRequest receives proper Message objects
            try:
                cleaned_msg = Message.from_dict(msg_dict)
                cleaned_messages.append(cleaned_msg)
            except Exception as e:
                # If reconstruction fails, log and keep original
                self._log_debug_event("message_reconstruction_error", {
                    "error": str(e),
                    "message": "Failed to reconstruct message from dictionary"
                })
                cleaned_messages.append(msg)
        
        # Log when annotations are stripped (for debugging)
        if annotations_found > 0:
            self._log_debug_event("annotations_stripped", {
                "count": annotations_found,
                "message": f"Stripped {annotations_found} annotation(s) from message history before sending to API"
            })
        
        return cleaned_messages
    
    def _agent_run(self) -> requests.Response:
        """
        Call the Cortex Agent REST API and return a streaming response.
        
        Returns:
            Streaming HTTP response
        
        Raises:
            Exception: If the API request fails
        """
        # Strip annotations from messages to prevent deserialization errors
        # (Cortex Search results in annotations can't be sent back to API)
        cleaned_messages = self._strip_annotations_from_messages(
            st.session_state[self.session_key]
        )
        
        request_body = DataAgentRunRequest(
            model=self.model,
            messages=cleaned_messages,
        )
        
        url = f"https://{self.host}/api/v2/databases/{self.database}/schemas/{self.schema}/agents/{self.agent}:run"
        
        # Build headers with optional warehouse and role
        headers = {
            "Authorization": f'Bearer {self.pat}',
            "Content-Type": "application/json",
        }
        
        # Add optional context headers if specified
        if self.warehouse:
            headers["X-Snowflake-Warehouse"] = self.warehouse
        if self.role:
            headers["X-Snowflake-Role"] = self.role
        
        try:
            resp = requests.post(
                url=url,
                data=request_body.to_json(),
                headers=headers,
                stream=True,
                verify=self.verify_ssl,
            )
                    
            if resp.status_code < 400:
                return resp
            else:
                    error_msg = f"Failed request with status {resp.status_code}: {resp.text}"
                    self._log_debug_event("api_error", {
                        "url": url,
                        "status_code": resp.status_code,
                        "response_text": resp.text,
                        "request_messages_count": len(st.session_state[self.session_key])
                    })
                    raise Exception(error_msg)
        except requests.exceptions.RequestException as e:
            self._log_debug_event("request_exception", {
                "url": url,
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            })
            raise
    
    def _stream_events(self, response: requests.Response):
        """
        Process and render streaming events from the agent response.
        
        Args:
            response: Streaming HTTP response from the agent
        """
        content = st.container()
        content_map = defaultdict(content.empty)
        buffers = defaultdict(str)
        spinner = st.spinner("Waiting for response...")
        spinner.__enter__()
        
        try:
            events = sseclient.SSEClient(response).events()
            for event in events:
                match event.event:
                    case "response.status":
                        spinner.__exit__(None, None, None)
                        data = StatusEventData.from_json(event.data)
                        # Log status event for debugging
                        self._log_debug_event("response.status", {
                            "message": data.message,
                            "raw_data": event.data
                        })
                        spinner = st.spinner(data.message)
                        spinner.__enter__()
                    case "response.text.delta":
                        data = TextDeltaEventData.from_json(event.data)
                        buffers[data.content_index] += data.text
                        content_map[data.content_index].write(buffers[data.content_index])
                    case "response.thinking.delta":
                        data = ThinkingDeltaEventData.from_json(event.data)
                        buffers[data.content_index] += data.text
                        expanded = st.session_state.get(self.thinking_setting_key, True)
                        content_map[data.content_index].expander(
                                "Thinking", expanded=expanded
                        ).write(buffers[data.content_index])
                    case "response.thinking":
                        data = ThinkingEventData.from_json(event.data)
                        expanded = st.session_state.get(self.thinking_setting_key, True)
                        content_map[data.content_index].expander(
                            "Thinking", expanded=expanded
                        ).write(data.text)
                    case "response.tool_use":
                        data = ToolUseEventData.from_json(event.data)
                        content_map[data.content_index].expander("Tool use").json(data)
                    case "response.tool_result":
                        data = ToolResultEventData.from_json(event.data)
                        content_map[data.content_index].expander("Tool result").json(data)
                    case "response.chart":
                        data = ChartEventData.from_json(event.data)
                        spec = json.loads(data.chart_spec)
                        content_map[data.content_index].vega_lite_chart(
                            spec,
                                width='stretch',
                        )
                    case "response.table":
                        data = TableEventData.from_json(event.data)
                        data_array = np.array(data.result_set.data)
                        column_names = [
                            col.name for col in data.result_set.result_set_meta_data.row_type
                        ]
                        content_map[data.content_index].dataframe(
                            pd.DataFrame(data_array, columns=column_names)
                        )
                    case "error":
                        data = ErrorEventData.from_json(event.data)
                        # Log detailed error information for debugging
                        self._log_debug_event("error", {
                            "code": data.code,
                            "message": data.message,
                            "raw_data": event.data
                        })
                        st.error(f"Error: {data.message} (code: {data.code})")
                        st.session_state[self.session_key].pop()
                        return
                    case "response":
                        data = Message.from_json(event.data)
                        st.session_state[self.session_key].append(data)
        except Exception as e:
            # Log streaming exceptions
            self._log_debug_event("streaming_exception", {
                "exception_type": type(e).__name__,
                "exception_message": str(e)
            })
            st.error(f"Error processing response: {str(e)}")
            if st.session_state[self.session_key]:
                st.session_state[self.session_key].pop()
            raise
        finally:
            spinner.__exit__(None, None, None)
    
    def _process_new_message(self, prompt: str) -> None:
        """
        Process a new user message and get agent response.
        
        Args:
            prompt: User's message text
        """
        message = Message(
            role="user",
            content=[MessageContentItem(TextContentItem(type="text", text=prompt))],
        )
        self._render_message(message)
        st.session_state[self.session_key].append(message)
        
        with st.chat_message("assistant"):
            with st.spinner("Sending request..."):
                response = self._agent_run()
            st.markdown(
                f"```request_id: {response.headers.get('X-Snowflake-Request-Id')}```"
            )
            self._stream_events(response)
    
    def _render_message(self, msg: Message):
        """
        Render a single message in the chat interface.
        
        Args:
            msg: Message object to render
        """
        with st.chat_message(msg.role):
            for content_item in msg.content:
                match content_item.actual_instance.type:
                    case "text":
                        st.markdown(content_item.actual_instance.text)
                    case "chart":
                        spec = json.loads(content_item.actual_instance.chart.chart_spec)
                        st.vega_lite_chart(spec, width='stretch')
                    case "table":
                        data_array = np.array(
                            content_item.actual_instance.table.result_set.data
                        )
                        column_names = [
                            col.name
                            for col in content_item.actual_instance.table.result_set.result_set_meta_data.row_type
                        ]
                        st.dataframe(pd.DataFrame(data_array, columns=column_names))
                    case _:
                        st.expander(content_item.actual_instance.type).json(
                            content_item.actual_instance.to_json()
                        )
    
    def render(self, container=None):
        """
        Render the complete chat interface.
        
        This method displays the chat title (if provided), conversation history,
        and chat input box. It handles user input and agent responses naturally
        using Streamlit's default chat layout.
        
        Args:
            container: Optional Streamlit container to render in (for tabs/columns)
        """
        # Use provided container or default to main
        ctx = container if container is not None else st
        
        if self.title:
            ctx.title(self.title)
        
        # Render conversation history naturally
        for message in st.session_state[self.session_key]:
            self._render_message(message)
        
        # Chat input at bottom (Streamlit handles positioning naturally)
        if user_input := ctx.chat_input(self.chat_input_placeholder):
            self._process_new_message(prompt=user_input)
    
    def clear_history(self):
        """Clear the conversation history and debug events for this chat instance."""
        st.session_state[self.session_key] = []
        st.session_state[self.debug_events_key] = []
    
    def get_message_count(self) -> int:
        """Get the number of messages in the conversation history."""
        return len(st.session_state[self.session_key])
    
    def render_thinking_toggle(self):
        """
        Render a checkbox to toggle thinking expander behavior.
        
        Returns:
            bool: Current state of the setting
        """
        current_value = st.session_state.get(self.thinking_setting_key, True)
        
        new_value = st.checkbox(
            "Keep 'Thinking' expanders open",
            value=current_value,
            key=f"{self.thinking_setting_key}_checkbox",
            help="When enabled, thinking responses stay expanded until manually closed. "
                 "When disabled, they collapse after completion."
        )
        
        st.session_state[self.thinking_setting_key] = new_value
        return new_value
    
    def render_debug_toggle(self):
        """
        Render a checkbox to toggle debug mode.
        
        Returns:
            bool: Current state of the setting
        """
        current_value = st.session_state.get(self.debug_setting_key, False)
        
        new_value = st.checkbox(
            "Show API debug info",
            value=current_value,
            key=f"{self.debug_setting_key}_checkbox",
            help="Display errors and status events from the Cortex Agent API"
        )
        
        st.session_state[self.debug_setting_key] = new_value
        return new_value
    
    def render_debug_panel(self):
        """
        Render debug events panel if debug mode is enabled.
        
        Displays recent API events and errors for troubleshooting.
        """
        if st.session_state.get(self.debug_setting_key, False):
            debug_events = st.session_state.get(self.debug_events_key, [])
            if debug_events:
                with st.expander("🐛 Debug Events", expanded=False):
                    st.caption(f"Showing last {len(debug_events)} events (max 50)")
                    # Show events in reverse chronological order
                    for event in reversed(debug_events):
                        event_type = event.get('event_type', 'unknown')
                        timestamp = event.get('timestamp', 'N/A')
                        
                        # Color code by event type
                        if event_type == "error" or "exception" in event_type:
                            st.error(f"**{event_type}** at {timestamp}")
                        elif event_type == "response.status":
                            st.info(f"**{event_type}** at {timestamp}")
                        else:
                            st.write(f"**{event_type}** at {timestamp}")
                        
                        st.json(event.get('data', {}))
                        st.divider()

