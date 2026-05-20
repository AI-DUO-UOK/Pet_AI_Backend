from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from chatbot.llm import llm
from chatbot.tools import analyze_pet_image
from chatbot.memory import memory

# Tools list - the @tool decorator in tools.py creates a LangChain tool
tools = [analyze_pet_image]

# Create the agent using the modern LangChain API
# create_agent returns a CompiledStateGraph that works with messages
_agent_graph = create_agent(
    model=llm,
    tools=tools,
    system_prompt="""You are a helpful veterinary assistant. You can analyze pet images to detect skin and eye diseases.
When a user provides an image path and asks about their pet's health, you should use the analyze_pet_image tool to analyze the image.
Always be compassionate and provide medical advice based on the analysis."""
)

class AgentExecutorWrapper:
    """Wrapper to provide .run() interface compatible with old AgentExecutor"""
    
    def __init__(self, graph, memory):
        self.graph = graph
        self.memory = memory
        
    def run(self, input_text: str, **kwargs) -> str:
        """
        Execute the agent with text input and return text output.
        Compatible with old initialize_agent().run() interface.
        """
        try:
            # Get chat history from memory
            memory_vars = self.memory.load_memory_variables({})
            chat_history = memory_vars.get('chat_history', '')
            
            # Build messages list with chat history and new input
            messages = []
            if chat_history:
                # Add previous messages from memory (simplified - just context)
                # In a full implementation, you'd parse the chat_history properly
                pass
            
            # Add the current input
            messages.append(HumanMessage(content=input_text))
            
            # Run the agent with the new API
            result = self.graph.invoke({"messages": messages})
            
            # Extract the final message from the result
            if isinstance(result, dict) and "messages" in result:
                messages_list = result["messages"]
                if messages_list:
                    # Get the last message (should be the agent's response)
                    last_message = messages_list[-1]
                    response_text = last_message.content if hasattr(last_message, 'content') else str(last_message)
                    return response_text
            
            # Fallback
            return str(result)
        except Exception as e:
            print(f"Agent execution error: {e}")
            import traceback
            traceback.print_exc()
            return f"I encountered an error: {str(e)}"

# Create the wrapper instance with .run() method
agent = AgentExecutorWrapper(_agent_graph, memory)