# Aspen
A watered idea blooms

## Tool Summary
Aspen is a modular, locally running AI agent focused on developer workflows. It primarily uses local models (small 4–7B models + one larger 27–32B model - think MOE but with models instead of sub-networks) for cost-efficiency, with optional cloud access for complex task planning, sanity checks, high level reasoning about the codebase, etc. But the core idea is that if a local model is allowed to run for long enough and try enough times in enough different ways, it will eventually solve the problem. Many developers (me) don't have tons of money to throw at API models, so I'm needing to create my own solution, and I think this could be helpful for others as well.

Aspen features a dispatch layer that routes tasks to different models. It is designed to be autonomous, handling task design and execution, errors, and retries by itself — including self-correcting behaviors like clearing context when stuck.

Users can walk away and let it work for hours, checking in only at major milestones. Imagine the user entering a prompt before they leave for work, and by the time they get home, Aspen is way beyond an MVP. Aspen can reach out to the user via text, phone call, email, Discord, or Slack to ask questions if really needed.

Aspen will (in the future) include an auto-update system that monitors model releases and swaps in better models automatically (if enabled), while keeping rollback options available.

The whole architecture is modular, extensible, and hot-swappable, allowing easy updates without major rebuilds.

## Technical Details
To make all of this work, there are several components and layers that need to be built.

### Tool Layer
Aspen will be a local program that you run from the terminal and the UI can be opened in a browser. It will need a pretty chunky toolbelt to actually be useful. Some common tools that existing CLI agents have are:

| Tool                | Description                                           | Permission Required |
|---------------------|-------------------------------------------------------|---------------------|
| AgentTool           | Runs a sub-agent to handle complex, multi-step tasks   | No                  |
| BashTool (Bash)     | Executes shell commands in your environment            | Yes                 |
| GlobTool            | Finds files based on pattern matching                  | No                  |
| GrepTool            | Searches for patterns in file contents                 | No                  |
| LSTool              | Lists files and directories                            | No                  |
| FileReadTool (View) | Reads the contents of files                            | No                  |
| FileEditTool (Edit) | Makes targeted edits to specific files                 | Yes                 |
| FileWriteTool (Replace) | Creates or overwrites files                      | Yes                 |
| NotebookEditTool    | Modifies Jupyter notebook cells                        | Yes                 |
| NotebookReadTool    | Reads and displays Jupyter notebook contents           | No                  |
| WebFetchTool        | Fetches content from a specified URL                   | Yes                 |

*source: https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview*

This is a good start, but Aspen will need several more:
- Ability to run a local web server
- Ability to take screenshots and review them
- Ability to use existing unit test frameworks
- Ability to search the web
- Ability to analyze PDF files

Essentially, any tools that a developer uses on a daily basis should be accessible to Aspen. Aspen should not have to constantly be asking for permission to do things - the user should sandbox Aspen as needed. This will be explained to users in the docs. Aspen will be treated with the same level of trust as a human developer, and the user can decide how much access to give Aspen.

### Dispatch Layer
This is the core routing layer that decides which model to use for a given task. This will probably need to be done by the largest local model in the collection. 

### Model Layer
I am not sure what the most optimal configuration here will be, but my first idea is use several small models for specific roles in the development process and one larger model for in depth code generation, project orchestration, etc. Then, the dispatcher can decide to call an API model every now and then to check in on the project, make sure the overall plan is still on track, etc.

---

## Project Structure

Currently the project is very empty. I have some very helpful research though:

1. [codex-cli](research/codex): an open source CLI agent that OpenAI released
2. [A Practical Guide to Building Agents](research/practical-guide-to-building-agents.md): an overview of how to build an agent, also by OpenAI
3. **Very valuable**: [System prompts from all leading AI agents](research/system-prompts-and-models-of-ai-tools): a directory containing the current system prompts for all leading AI agents, organized by the tool name or model name. this will be hugely helpful for quickly designing a very effective system prompt for Aspen.

We will be using these as a guide to build Aspen.

## Current Tasks
1. Define a core implementation plan
2. Decide on a tech stack
3. Start building an MVP

