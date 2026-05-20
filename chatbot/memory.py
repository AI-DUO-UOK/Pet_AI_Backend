from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

class SimpleConversationMemory(BaseChatMessageHistory):
    """Simple in-memory conversation memory that stores messages."""
    
    def __init__(self):
        self.messages = []
        self.memory_key = "chat_history"
        
    def add_messages(self, messages):
        """Add messages to memory."""
        if not isinstance(messages, list):
            messages = [messages]
        self.messages.extend(messages)
    
    def add_user_message(self, message: str):
        """Add a user message."""
        self.add_messages(HumanMessage(content=message))
    
    def add_ai_message(self, message: str):
        """Add an AI message."""
        self.add_messages(AIMessage(content=message))
    
    def save_context(self, inputs: dict, outputs: dict):
        """Save context from inputs and outputs (for compatibility)."""
        if "input" in inputs:
            self.add_user_message(str(inputs["input"]))
        if "output" in outputs:
            self.add_ai_message(str(outputs["output"]))
    
    def load_memory_variables(self, inputs: dict):
        """Load memory variables for use in prompts/agents."""
        # Convert messages to a string representation
        chat_history_str = "\n".join([
            f"{msg.__class__.__name__}: {msg.content}" 
            for msg in self.messages
        ])
        return {
            self.memory_key: chat_history_str,
            "chat_history": chat_history_str
        }
    
    @property
    def messages_list(self):
        """Get list of messages for the agent."""
        return self.messages.copy()
    
    def clear(self):
        """Clear all messages."""
        self.messages = []

# Initialize conversation memory for the chatbot
# This keeps track of the conversation history for context
memory = SimpleConversationMemory()