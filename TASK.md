# TASK.md

## Task Management

This file tracks ongoing, completed, and planned tasks for the Japanese Lexical Graph project.

**Date Format**: YYYY-MM-DD

---

### Current & Upcoming Tasks

*   **Task ID**: DOC-001
    *   **Task**: Initialize project documentation (`PLANNING.MD`, `TASK.MD`).
    *   **Description**: Create initial `PLANNING.MD` with project guidelines and `TASK.MD` for task tracking structure.
    *   **Assigned to**: AI Assistant
    *   **Status**: In Progress
    *   **Date Added**: YYYY-MM-DD
    *   **Priority**: High
    *   **Sub-tasks**:
        *   [x] Draft content for `PLANNING.MD`.
        *   [ ] Draft initial structure and content for `TASK.MD`.

*   **Task ID**: FEAT-001
    *   **Task**: Review and Refine Core AI Features.
    *   **Description**: Ensure AI-powered term explanations, comparisons, and lexical data enrichment (`ai_generation_single.py`) are robust, accurate, and user-friendly.
    *   **Assigned to**:
    *   **Status**: To Do
    *   **Date Added**: YYYY-MM-DD
    *   **Priority**: High

*   **Task ID**: FEAT-002
    *   **Task**: Enhance Interactive Learning Module (`exercises_script.py`).
    *   **Description**: Improve exercise generation logic, conversation flow, level differentiation, and feedback mechanisms in the learning module.
    *   **Assigned to**:
    *   **Status**: To Do
    *   **Date Added**: YYYY-MM-DD
    *   **Priority**: High

*   **Task ID**: FEAT-003
    *   **Task**: Implement selectable LLM model for Gemini API calls.
    *   **Description**: Add the ability to select different LLM models for Gemini API calls.
    *   **Assigned to**:
    *   **Status**: To Do
    *   **Date Added**: YYYY-MM-DD
    *   **Priority**: High
    *   **Sub-tasks**:
        *   [x] Add `GEMINI_DEFAULT_MODEL` to `.env` and `config.py`.
        *   [x] Create `config.py` for managing configurations.
        *   [x] Refactor `gemini_helper.py` to use `config.py` for API key and default model.
        *   [x] Update `gemini_helper.py` functions to accept `model_name` and use it or the configured default.
        *   [x] Remove hardcoded model fallbacks/lists from `gemini_helper.py` in favor of direct model usage.
        *   [x] Update relevant API endpoints in `app.py` (`/gemini-explanation`, `/gemini-analyze`, `/enhanced-node`) to optionally accept `model_name` query parameter and pass it to helper functions.
        *   [x] Update `PLANNING.md` to reflect model selection configurability.
        *   [x] Update `README.md` to document model selection and new .env variable.

---

### Completed Tasks

*   **Task ID**: INIT-001
    *   **Task**: Initial project setup and core graph visualization.
    *   **Description**: Basic Flask app, NetworkX graph loading, and 3D visualization with Three.js.
    *   **Status**: Completed
    *   **Date Completed**: (Please fill in - assumed prior to this session)
    *   **Notes**: Further frontend refinements may be needed.

*   **Task ID**: DOC-000
    *   **Task**: Create comprehensive `ABOUT.md`.
    *   **Description**: Document application features, including AI capabilities and file structure.
    *   **Status**: Completed
    *   **Date Added**: YYYY-MM-DD
    *   **Date Completed**: YYYY-MM-DD

*   **Task ID**: BUGFIX-004
    *   **Task**: Normalize edge 'weight' attribute after graph load
    *   **Description**: Added logic in `app.py` to map `synonym_strength` to a numeric `weight` attribute so downstream functions relying on `weight` work correctly.
    *   **Status**: Completed
    *   **Date Completed**: 2025-05-18
    *   **Notes**: Also added unit test `tests/unit/test_graph_weights.py` to ensure at least some edges expose a valid `weight`.

*   **Task ID**: UI-004
    *   **Task**: Remove 'Show Raw API Response' accordion from Gemini panel
    *   **Description**: Deleted HTML generation in `static/js/main.js` to prevent displaying raw API response accordion.
    *   **Status**: Completed
    *   **Date Completed**: 2025-05-18

*   **Task ID**: BUGFIX-005
    *   **Task**: Keep in-memory graph in sync after AI generation
    *   **Description**: Refactor `ai_generation_single.py` to accept shared NetworkX graph instance and update `app.py` so newly generated nodes/edges are immediately available for visualisation without server restart.
    *   **Assigned to**: AI Assistant
    *   **Status**: Completed
    *   **Date Completed**: 2025-05-18

*   **Task ID**: BUGFIX-006
    *   **Task**: Fix hamburger menu not opening
    *   **Description**: Added `#side-nav.open` CSS rule in `static/css/styles.css` to override `width: 0` and `left: 0` conflicts, ensuring the side navigation panel expands when the hamburger icon is clicked.
    *   **Status**: Completed
    *   **Date Completed**: 2025-05-19
    *   **Notes**: Root cause was CSS specificity where `#side-nav` (id selector) had higher precedence over `.menu-nav.open`. Added override rule with higher specificity.

---

### Discovered During Work / General TODOs

*(Use this section to jot down smaller tasks, ideas, or bugs that arise during development)*

*   [ ] **Refactor**: Consider adding more explicit error handling and logging for API calls in `gemini_helper.py` and `wikidata_helper.py`.
*   [ ] **Research**: Evaluate effectiveness and potential improvements for the current caching strategy, especially for `exercises_script.py` and `gemini_helper.py`.
*   [ ] **Maintenance**: Correct typo in filename `excercises_instruction.txt` to `exercises_instruction.txt` and update references.
*   [ ] **Testing**: Develop a comprehensive test suite with Pytest, starting with critical modules like `gemini_helper.py` and `exercises_script.py`.
*   [ ] **Frontend**: Plan for UI/UX improvements for the graph visualization and learning module interaction.

--- 