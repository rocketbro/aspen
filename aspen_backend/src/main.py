from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk
# Removed legacy agent imports
# from langchain.agents import AgentExecutor, create_react_agent
# from langchain import hub
# from langchain.prompts import PromptTemplate
from fastapi.responses import StreamingResponse
import json
# Removed callback imports
# from typing import Any, Dict, List, Optional
# from langchain_core.callbacks import BaseCallbackHandler
# from langchain_core.outputs import LLMResult

# LangGraph imports
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
# Remove StateGraph, MessagesState, START import

# Import our tools
from src.tools.file_system_tools import FileReadTool, ListDirectoryTool, GrepTool, FileWriteTool, FileEditTool

# --- Removed Custom Callback Handler ---
# class PrintPromptHandler(BaseCallbackHandler):
#     ...
# print_prompt_handler = PrintPromptHandler()
# --------------------------------------------

# --- Global State for Thinking Mode (Keep for future use?) ---
enable_thinking_mode = False  # Default to True as per Qwen3 docs

# Define the request body model
class ChatRequest(BaseModel):
    message: str
    # Add chat history later if needed
    # chat_history: list[tuple[str, str]] = []

# --- Agent Setup ----

# Initialize LLM (Removed callback handler)
llm = ChatOllama(model="qwen3:4b")

# Instantiate tools
tools = [
    FileReadTool(),
    ListDirectoryTool(),
    GrepTool(),
    FileWriteTool(),
    FileEditTool()
    ]

# --- Removed Prompt Template Logic ---
# with open("src/prompts/react_agent_prompt.txt", "r") as f:
#     template = f.read()
# template = (...)
# prompt = PromptTemplate(...)
# prompt.input_variables = [...]
# -------------------------------------

# --- LangGraph Setup ---
# Instantiate memory saver
memory = MemorySaver()

# Restore the LangGraph agent
agent_graph = create_react_agent(llm, tools, checkpointer=memory)

# --- FastAPI App ---

app = FastAPI(title="Aspen Backend")

# Simple test endpoint to check direct LLM streaming
@app.post("/test_llm_stream")
async def test_llm_stream(request: ChatRequest):
    """Directly streams response from the base LLM to test streaming."""
    async def stream_llm():
        try:
            print("--- DEBUG: Testing direct LLM stream ---")
            async for chunk in llm.astream(request.message):
                # chunk is typically an AIMessageChunk here
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    print(f"--- DEBUG: LLM yielding: {repr(chunk.content)} ---")
                    yield json.dumps({"text": chunk.content}) + "\\n"
                else:
                    print(f"--- DEBUG: LLM received non-AIMessageChunk or empty: {type(chunk)} ---")
            print("--- DEBUG: LLM stream finished ---")
        except Exception as e:
            error_message = json.dumps({"error": str(e)}) + "\\n"
            print(f"--- ERROR: Exception during direct LLM stream: {e} ---")
            import traceback
            traceback.print_exc()
            yield error_message
        finally:
            print("--- DEBUG: Exiting direct LLM stream generator ---")

    return StreamingResponse(stream_llm(), media_type="application/x-ndjson")

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


# Modified chat endpoint to use the LangGraph agent and stream responses
@app.post("/agent_chat")
async def agent_chat_endpoint(request: ChatRequest):
    """Receives a message and streams the agent's step-level responses back."""

    async def stream_agent_response():
        """Async generator to stream agent execution steps using LangGraph agent."""
        agent_input = {"messages": [HumanMessage(content=request.message)]}
        config = {"configurable": {"thread_id": "user_session_1"}}

        print("--- DEBUG: Starting agent stream (step-level) ---")
        stream_chunk_count = 0

        try:
            # Use agent_graph.astream with stream_mode="messages"
            async for step, metadata in agent_graph.astream(agent_input, config=config, stream_mode="messages"):
                stream_chunk_count += 1
                print(f"--- DEBUG: Received stream tuple {stream_chunk_count}: ---")
                print(f"STEP: {type(step)} - {step}")
                print(f"METADATA: {metadata}")
                print("--- END DEBUG TUPLE ---")

                # Only yield if this is a message from the agent node
                if metadata.get("langgraph_node") == "agent":
                    if isinstance(step, AIMessageChunk) and step.content:
                        text_chunk = step.content
                        print(f"--- DEBUG: Yielding text chunk from agent: {repr(text_chunk)} ---")
                        yield json.dumps({"text": text_chunk}) + "\n"
                    else:
                        print(f"--- DEBUG: Agent step is not AIMessageChunk or has no content: {type(step)} ---")
                else:
                    pass

            print(f"--- DEBUG: Agent stream finished after {stream_chunk_count} chunks ---")

        except Exception as e:
            error_message = json.dumps({"error": str(e)}) + "\n"
            print(f"--- ERROR: Exception during agent execution stream: {e} ---")
            import traceback
            traceback.print_exc()
            yield error_message
        finally:
             print("--- DEBUG: Exiting stream_agent_response generator ---")

    return StreamingResponse(stream_agent_response(), media_type="application/x-ndjson")

# Remove or comment out the old /chat endpoint if desired
# @app.post("/chat")
# async def chat_endpoint(request: ChatRequest):
#     ... 