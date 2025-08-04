## task: `v0.3.3-dev.250731.ui-style-optimization`

===

**TODAY's DATE:** [2025-07-31]

**WORK TASK OBJECTIVES:** "web-ui-style-optimization"


### Task Plan Details and Design Solution Document:

- Original Task Requirements: @task-todo/250731-1/Original-Task-Requirements.md
- @task-todo/250731-1/DSAgents-UI-Implementation-Plan.md
- @task-todo/250731-1/DSAgents-UI-DesignSystem-Specification.md
- @task-todo/250731-1/DSAgents-UI-DesignLanguage-Solution.md

[webtui](https://github.com/webtui/webtui)
- [dev-docs](https://context7.com/webtui/webtui/llms.txt?tokens=23249)

### Attention⚠️!

1. When implementing front-end code modifications, be sure to make changes according to our current codebase's back-end interfaces and front-end project. Before modifying any front-end components, first `tree` search the current front-end project and `src/api/v2/web_ui.py`, then proceed with the modification. Do not fix or build front-end components arbitrarily!

2. If you are unsure about how to use the `WebTUI` CSS library, please read the WebTUI CSS library Docs (Use your context7 MCP tool to read the `WebTUI` CSS library Docs).

===

## Task1: [DeepSearchAgents WebUI Overall "Design Language" & "Design System" Optimization for Design Plan]

### Sub-Task(1.1) UI "Design Language"

DeepSearchAgents-CodeAgent Web UI Style: TUI Style Web-TUI
Elegant&SuperCool Web-TUI Style UI for "DeepSearchAgents-CodeAgent" Execution (DeepResearch Multi-step Task) The running process details are displayed to human users through the Web UI.

> `DeepSearchAgents's CodeAgent is super cool "Executable Code Actions Elicit Better LLM Agents".`
```
**DS(DeepSearch)CodeAgent** ReAct(*"Synergizing Reasoning and Acting in Language Models"*) Base Loop:
1.Think("LLM Reasoning" text output content)--> 2.Action("LLM Actions" structured output content)--> 3.Observation(System running agent's actions results and callback to LLM to observe the effects of its actions for further reasoning.) ReAct

*CodeAct-CodeAgent is a special type of ReAct Agent that uses executable code as the output for Actions.*

**DSCodeAgent** DS Task Base Workflow Loop:
1. [PlaningStep]: Initialization Planning for Task Initialization (Agent Thinking and Writing Task Solutions & Execution Plans)
2. ActionStep-(N): (2.1)Agent begins to execute the plan according to the task scheme. Before executing each step, it will first output the current step's reasoning"Action Thinking..." and then output the action for that step - ```python CodeAction (Py script code). (2.2)After the system receives the CodeAction output from the LLM, it extracts the Python code and runs the script in its sandbox (if the script calls custom Agent tool functions within the system, it will execute the corresponding function call logic to obtain the function execution results returned to the CodeAction logic within the script), and outputs all final script execution results. The system then returns all sandbox execution results back to the Agent for observation and feedback to consider its next ActionStep.
3. ActionStep-(N+1): First observe the execution result of the previous ActionStep CodeAction, then output the next action to be performed as "Action Thinking..." + ```python CodeAction. The system receives CodeAction ...
4. PlaningStep: Update Planing  Trigger "planning_interval ...
5. ActionStep: ActionSteps Loop Steps in the new interval planning cycle ...
6. FinalAnswerStep: When the Agent observes that the results of the previous step and all steps executed in its task memory meet its own task plan objectives, the Agent will output the final DeepResearch Report. When outputting the final result CodeAction, a special "FinalAnswer" Agent tool will be invoked. "Final Answer Action Thinking..." + ```python CodeAction. The system receives CodeAction ... call Final Answer Tool ... returns the final DeepResearch Report to the user for display.
```

**Core Design Emotional Communication**

The design language needs to convey the characteristics of CodeAgent executing multi-step tasks according to the CodeAct paradigm, fully showcasing its core traits: "Code is Action!", "CodeActions Can do ANYTHING!", "Plan first, then execute", "Periodic planning & multi-step execution", and "Think before acting". The goal is to create a frontend interface through deeply researched design language that allows human users to transparently, clearly, and accurately observe the entire process of an Agent performing multi-step tasks. This will enable users to develop full trust in AI Agents of the CodeAgent type and their powerful capabilities in executing complex task sequences.

**Design style Keywords:**
`CodeAct`, `CodeAgent`, `ActionCode`, `CodeActions`, `AI Agent Programmer`, `TUI`, `WebTUI`, `Terminal`, `Neovim`, `SandBox-Web-TUI-Agent-IDE(like Neovim)`, `SandBox-Web-TUI-Agent-Terminal`, `LLM Streaming`, `"Berkeley Mono @usgraphics"`, `monospace`, `text-heavy markdown`, `font-family: Berkeley Mono / SF Mono / monospace / Apple Color Emoji`, `claude code CLI style`...

===

### Sub-Task(1.2) UI "Design system" Specification

#### Themes(Colors/TUI-Font/TUI-Icon)

`WebTUI` Web UI can use Theme-Switcher (Globally supports various open-source IDE/Terminal code TUI style themes. e.g., GitHub, Monospace, Monoxxx..., TokyoNight...) style themes.

#### components types

ChatMessage
- User Chat Message (Input box & task message sent by user)
- Agent Chat Message Cards component with multiple types and styles

CodeAct CodeAgent ActionCode User Watch Window & CodeActions Execution Result User Watch Window
- Web IDE Top Right Sidebar Component
- Web Terminal Bottom Right Sidebar Component
- ...

#### Agent ChatMessage - Agent Running Task frontend status with dynamic [status text + TUI style dynamic Badge]

[PlanStep] **"(Planing)Thinking..."**
[PlanStep] **"(Initial/Update)Planing..."**

[ActionStep] **"(Action)Thinking..."**
[ActionStep] **"Coding..."**
[ActionStep] **"Actions Running..."**

[FinalAnswerStep] **"Writing..."**

[General status] **"Working..."**

- "Thinking..." (for the system loading process of the next event transmission loading ,TUI-UX dynamic skeleton)
- "Planing..." (Frontend streaming reception & rendering of PlanStep's plan content process event transmission loading ,TUI-UX dynamic skeleton)
- "Coding..." (Frontend streaming reception & rendering of ActionStep's content process event transmission loading ,TUI-UX dynamic skeleton)
- "Actions Running..." (The waiting sandbox running status before the next ActionStep system's LLM request call, TUI-UX dynamic skeleton)
- "Writing..." (Frontend streaming reception & rendering of FinalAnswerStep's content process event transmission loading ,TUI-UX dynamic skeleton)
- "Working..." (Any program running status other than "Actions Running..."—which is clearly obtainable within our system—if it is impossible to determine a definite waiting streaming response event after a system LLM request, or before starting to receive the streaming response event after sending the request, then the general Agent running status displayed on the common front-end WebTUI should be shown.)

===

### Sub-Task(1.3) "Design Language"&"Design system" plan for UI Design Implementation Tech Stack

base old `ui.shadcn` with `Next.js` Mix New `WebTUI` for "WebTUI Monospace"

#### Web-TUI style CSS library: `WebTUI`

[webtui](https://github.com/webtui/webtui)

- [dev-docs](https://context7.com/webtui/webtui/llms.txt?tokens=23249)

**WebTUI** is a **CSS library** that brings the beauty of **Terminal User Interfaces** (TUIs) to the browser

Features:
- **Modular Design Approach** - Use and import only what you need
- **CSS Layer Precedence** - Uses CSS layers [[MDN Reference]](https://developer.mozilla.org/en-US/docs/Web/CSS/@layer) so you rarely have to use !important
- **Purist Approach** - Designed to be used with minimal markup and CSS

**Install**
Install the `WebTUI` package with `Next.js`
```
*bun* i @webtui/css
*npm* i @webtui/css
*yarn* add @webtui/css
*pnpm* install @webtui/css
```

Define the order of layers and import the base stylesheet in `globals.css`
```
@layer base, utils, components;

@import "@webtui/css/base.css";
```

Import additional utilities, components, and themes in `globals.css`
```
@layer base, utils, components;

@import "@webtui/css/base.css";

*/* Utils */*
@import "@webtui/css/utils/box.css";

*/* Components */*
@import "@webtui/css/components/button.css";
@import "@webtui/css/components/typography.css";
```

ESM imports can be used to scope styles to specific components
```
import "@webtui/css/components/button.css";

type *Props* = {
  */* ... */*
};

export default function *Button*(*props*: *Props*) {
  return <button>{props.children}</button>;
}
```
