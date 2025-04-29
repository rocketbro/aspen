# Placeholder for tool definitions 

import os
import subprocess
from pathlib import Path
from pydantic.v1 import BaseModel, Field # Use v1 for Langchain compatibility
from typing import Type

from langchain.tools import BaseTool

# Define common base path (workspace root relative to this file)
# Adjust this if your execution context changes
WORKSPACE_ROOT = Path(__file__).parent.parent.parent


class FilePathInput(BaseModel):
    file_path: str = Field(description="Relative path to the file within the workspace")

class ListDirectoryInput(BaseModel):
    dir_path: str = Field(description="Relative path to the directory within the workspace", default=".")

class GrepInput(BaseModel):
    pattern: str = Field(description="The regex pattern to search for")
    path: str = Field(description="Relative path to the file or directory to search within", default=".")


class FileReadTool(BaseTool):
    name: str = "read_file"
    description: str = "Reads the content of a specified file. Input should be the relative path to the file."
    args_schema: Type[BaseModel] = FilePathInput

    def _run(self, file_path: str) -> str:
        """Reads a file."""
        try:
            full_path = (WORKSPACE_ROOT / file_path).resolve()
            # Security check: Ensure the path is within the workspace root
            if WORKSPACE_ROOT not in full_path.parents and full_path != WORKSPACE_ROOT:
                 return f"Error: Access denied. Path is outside the allowed workspace: {file_path}"
            if not full_path.is_file():
                return f"Error: File not found at {file_path}"
            with open(full_path, 'r', encoding='utf-8') as f:
                # Limit read size for safety, consider adding start/end lines later
                content = f.read(5000) # Limit to 5000 chars for now
                if len(f.read()) > 0:
                    content += "\n... (file truncated due to length)"
                return content
        except Exception as e:
            return f"Error reading file {file_path}: {e}"

    async def _arun(self, file_path: str) -> str:
        # For now, just use the sync version. Can implement async file IO later if needed.
        return self._run(file_path)


class ListDirectoryTool(BaseTool):
    name: str = "list_directory"
    description: str = "Lists the contents (files and directories) of a specified directory. Input is the relative path to the directory."
    args_schema: Type[BaseModel] = ListDirectoryInput

    def _run(self, dir_path: str = ".") -> str:
        """Lists directory contents."""
        try:
            full_path = (WORKSPACE_ROOT / dir_path).resolve()
            # Security check
            if WORKSPACE_ROOT not in full_path.parents and full_path != WORKSPACE_ROOT:
                 return f"Error: Access denied. Path is outside the allowed workspace: {dir_path}"
            if not full_path.is_dir():
                return f"Error: Directory not found at {dir_path}"

            items = []
            for item in os.listdir(full_path):
                item_path = full_path / item
                item_type = "[dir]" if item_path.is_dir() else "[file]"
                items.append(f"{item_type} {item}")
            return "\n".join(items) if items else "Directory is empty."
        except Exception as e:
            return f"Error listing directory {dir_path}: {e}"

    async def _arun(self, dir_path: str = ".") -> str:
        return self._run(dir_path)


class GrepTool(BaseTool):
    name: str = "search_file_content"
    description: str = (
        "Searches for a specific regex pattern within a file or directory using ripgrep (rg). "
        "Input requires 'pattern' (regex) and optionally 'path' (relative path, default is current directory '.'). "
        "Remember to escape regex special characters in the pattern if needed."
    )
    args_schema: Type[BaseModel] = GrepInput

    def _run(self, pattern: str, path: str = ".") -> str:
        """Uses ripgrep (rg) to search for a pattern."""
        try:
            full_path = (WORKSPACE_ROOT / path).resolve()
            # Security check
            if WORKSPACE_ROOT not in full_path.parents and full_path != WORKSPACE_ROOT:
                 return f"Error: Access denied. Path is outside the allowed workspace: {path}"

            # Basic command construction (consider adding more rg flags like --max-count, --glob)
            command = ["rg", "--max-count=50", "--glob=!{.git,node_modules,.venv/*}", "-e", pattern, str(full_path)]

            result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=WORKSPACE_ROOT)

            if result.returncode == 0:
                return result.stdout if result.stdout else "Pattern found, but no specific lines matched (or rg configuration hides them)."
            elif result.returncode == 1:
                return "Pattern not found."
            else:
                return f"Error running grep (ripgrep): {result.stderr}"
        except FileNotFoundError:
             return "Error: 'rg' (ripgrep) command not found. Please ensure ripgrep is installed and in your PATH."
        except Exception as e:
            return f"Error running grep: {e}"

    async def _arun(self, pattern: str, path: str = ".") -> str:
        # Subprocess can be tricky to make truly async without asyncio.subprocess
        # For now, we run it synchronously in the async context
        # Consider libraries like 'asyncio.subprocess' or 'anyio' for true async later
        return self._run(pattern, path) 