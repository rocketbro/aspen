from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import AgentExecutor, create_react_agent
from langchain import hub

# Import our tools
from src.tools.file_system_tools import FileReadTool, ListDirectoryTool, GrepTool

# --- Global State for Thinking Mode ---
enable_thinking_mode = False  # Default to True as per Qwen3 docs

# Define the request body model
class ChatRequest(BaseModel):
    message: str
    # Add chat history later if needed
    # chat_history: list[tuple[str, str]] = []

# --- Agent Setup ----

# Initialize LLM
llm = ChatOllama(model="qwen3:8b")

# Instantiate tools
tools = [FileReadTool(), ListDirectoryTool(), GrepTool()]

# Pull the ReAct prompt from LangChain Hub
prompt = hub.pull("hwchase17/react")

# Create the agent - uses the hub prompt now
agent = create_react_agent(llm, tools, prompt)

# Create the agent executor
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- FastAPI App ---

app = FastAPI(title="Aspen Backend")

# --- Thinking Mode Toggle Endpoint ---
@app.post("/toggle_thinking_mode")
def toggle_thinking():
    """Toggles the Qwen3 thinking mode (/think, /no_think)."""
    global enable_thinking_mode
    enable_thinking_mode = not enable_thinking_mode
    return {"message": f"Thinking mode set to: {enable_thinking_mode}"}


@app.get("/")
def read_root():
    return {"message": "Welcome to the Aspen Backend"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


# Modified chat endpoint to use the agent
@app.post("/agent_chat")
async def agent_chat_endpoint(request: ChatRequest):
    """Receives a message and uses the agent executor to respond."""
    global enable_thinking_mode
    try:
        # Prepend command based on thinking mode state
        prefix = "/think " if enable_thinking_mode else "/no_think "
        modified_message = prefix + request.message

        # Use agent_executor.ainvoke for asynchronous execution
        # Hub prompt typically expects 'input' and handles intermediate steps
        response = await agent_executor.ainvoke({
            "input": modified_message,
            # Removed explicit passing of tools/agent_scratchpad
        })
        # The final answer is usually in the 'output' key
        return {"response": response.get('output', 'Agent did not produce final output.')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Remove or comment out the old /chat endpoint if desired
# @app.post("/chat")
# async def chat_endpoint(request: ChatRequest):
#     ... 