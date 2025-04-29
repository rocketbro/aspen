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

# --- New Tools --- 

class FileWriteInput(BaseModel):
    file_path: str = Field(description="Relative path to the file within the workspace to create or overwrite.")
    content: str = Field(description="The full content to write to the file.")

class FileWriteTool(BaseTool):
    name: str = "write_file"
    description: str = "Creates a new file or completely overwrites an existing file with the provided content. Use 'edit_file' for modifications. Input requires 'file_path' (relative path) and 'content'."
    args_schema: Type[BaseModel] = FileWriteInput

    def _run(self, file_path: str, content: str) -> str:
        """Writes content to a file, overwriting if it exists."""
        try:
            full_path = (WORKSPACE_ROOT / file_path).resolve()
            # Security check: Ensure the path is within the workspace root and not manipulating directories above
            if WORKSPACE_ROOT not in full_path.parents and full_path.parent != WORKSPACE_ROOT:
                 return f"Error: Access denied. Path is outside the allowed workspace or attempts directory traversal: {file_path}"
            
            # Create parent directories if they don't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote content to {file_path}"
        except Exception as e:
            return f"Error writing file {file_path}: {e}"

    async def _arun(self, file_path: str, content: str) -> str:
        return self._run(file_path, content)


class FileEditInput(BaseModel):
    file_path: str = Field(description="Relative path to the file within the workspace to edit.")
    code_edit: str = Field(
        description="The precise code changes to apply. Use comments like '# ... existing code ...' (adjusting for language) to represent unchanged sections between your edits. The tool will replace sections of the original file based on this structure."
    )

class FileEditTool(BaseTool):
    name: str = "edit_file"
    description: str = (
        "Applies structured code edits to an existing file. "
        "Takes a 'code_edit' string that specifies exact changes, using comments like '# ... existing code ...' "
        "(adjust comment style for the target language) to indicate unchanged blocks. "
        "Use 'write_file' to create or fully replace a file. "
        "Input requires 'file_path' (relative path) and 'code_edit'."
    )
    args_schema: Type[BaseModel] = FileEditInput

    def _run(self, file_path: str, code_edit: str) -> str:
        """Applies structured edits to a file."""
        try:
            full_path = (WORKSPACE_ROOT / file_path).resolve()
            # Security check
            if WORKSPACE_ROOT not in full_path.parents and full_path != WORKSPACE_ROOT:
                 return f"Error: Access denied. Path is outside the allowed workspace: {file_path}"
            if not full_path.is_file():
                return f"Error: File not found at {file_path}"

            # --- Read Original File --- 
            with open(full_path, 'r', encoding='utf-8') as f:
                original_lines = f.readlines()

            # --- Parse code_edit and Apply Changes --- 
            # Basic parsing assuming '# ... existing code ...' or similar standard comment markers
            # A more robust parser would detect language and use appropriate comment syntax
            # For now, we'll crudely look for lines starting with comment markers common in Python/JS/etc.
            # and containing '... existing code ...'
            import re
            # Regex to find 'existing code' markers (e.g., #, //, /*, --) potentially with leading whitespace
            marker_pattern = re.compile(r"^\\s*(#|//|--|\\\*\\*?|/\*).*existing code.*") 
            
            edit_lines = code_edit.strip().split('\n')
            
            new_file_lines = []
            original_line_idx = 0
            edit_line_idx = 0

            while edit_line_idx < len(edit_lines):
                edit_line = edit_lines[edit_line_idx]
                is_marker = marker_pattern.match(edit_line)

                if is_marker:
                    # Find the next non-marker line in the edit
                    next_edit_marker_idx = -1
                    for i in range(edit_line_idx + 1, len(edit_lines)):
                        if marker_pattern.match(edit_lines[i]):
                            next_edit_marker_idx = i
                            break
                    
                    # Determine corresponding lines in original file
                    # This is the tricky part and relies on the LLM generating correct context.
                    # A simple approach: Advance in original until the context *after* the marker matches.
                    # This is fragile. A diff-based approach would be more robust but complex.
                    
                    # Heuristic: Assume the marker corresponds to the current position in original_lines
                    # If the *next* line in edit_lines is also a marker, it implies skipping original lines.
                    if edit_line_idx + 1 < len(edit_lines) and marker_pattern.match(edit_lines[edit_line_idx+1]):
                         # LLM wants to skip some original code block
                         # We need a way to know how much to skip. This format doesn't specify explicitly.
                         # Let's *assume* (dangerous!) the LLM provided the *next* block of code it wants *after* the skip.
                         # We search forward in original_lines for the start of that next block.
                         next_code_block_start_in_edit = ""
                         for i in range(edit_line_idx + 2, len(edit_lines)):
                            if not marker_pattern.match(edit_lines[i]):
                                next_code_block_start_in_edit = edit_lines[i]
                                break
                        
                         if next_code_block_start_in_edit:
                             found_match = False
                             search_start_idx = original_line_idx
                             while original_line_idx < len(original_lines):
                                 if original_lines[original_line_idx].strip() == next_code_block_start_in_edit.strip():
                                      # Found the start of the next block LLM wants, skip complete.
                                      found_match = True
                                      break
                                 original_line_idx += 1
                             if not found_match:
                                 # If we can't find the next block, the edit is likely ambiguous/malformed
                                 original_line_idx = search_start_idx # backtrack search
                                 return f"Error: Ambiguous edit. Could not determine how much original code to skip based on marker at edit line {edit_line_idx + 1}. Edit:\n{code_edit}"
                         else: 
                             # Two markers in a row, but no code after? Assume skip to end of original file.
                             original_line_idx = len(original_lines) 
                   
                    edit_line_idx += 1 # Consume the marker line
                else:
                    # This is a line of new/edited code to add
                    new_file_lines.append(edit_line + '\n')
                    edit_line_idx += 1
                    # Crucially, when adding new code, we *don't* advance original_line_idx
                    # unless the LLM explicitly used markers to skip original lines.
                    # This assumes insertions/replacements happen *in place* conceptually.
                    # If the LLM intended replacement, it should have marked the code to be replaced
                    # with markers before and after the replacement block. 
                    # If the edit implies replacing original lines *without markers*, this simple logic fails.
                    # We might need to *advance* original_line_idx if we are conceptually *replacing* 
                    # based on context, but that's hard to infer reliably without diff/patch logic.
                    # For now, let's stick to the simpler interpretation: Markers skip, code adds/inserts.
                   
            # After processing edit lines, append any remaining original lines if the edit didn't end with a skip-to-end
            # Check if the last processed edit line was NOT a marker implying skip-to-end
            last_line_was_marker = marker_pattern.match(edit_lines[-1]) if edit_lines else False
            # This logic needs refinement: how do we know if the last marker meant skip *some* or skip *all remaining*?
            # Heuristic: if the edit finished, and we haven't reached the end of original, append the rest.
            if original_line_idx < len(original_lines):
                 new_file_lines.extend(original_lines[original_line_idx:])

            # --- Write New File Content --- 
            with open(full_path, 'w', encoding='utf-8') as f:
                f.writelines(new_file_lines)
               
            return f"Successfully applied edits to {file_path}"
        except Exception as e:
            return f"Error editing file {file_path}: {e}\nEdit attempted:\n{code_edit}"

    async def _arun(self, file_path: str, code_edit: str) -> str:
        # As this involves file I/O, run synchronously for now.
        return self._run(file_path, code_edit) 