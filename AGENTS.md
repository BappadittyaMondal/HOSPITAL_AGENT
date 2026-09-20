# AGENTS.md - Autonomous Execution & Operational Rules

## 1. Autonomous Execution & Reduced Permission Invariant ("Reduce Ask Permission to Continue")
- **Pre-Granted Authorization:** The user has explicitly granted full permission to build, test, modify, run, debug, verify, and maintain this project.
- **Eliminate Permission-Asking Loops:** Never pause, prompt, or halt execution to ask for user permission, confirmation, or approval to proceed to the next step, phase, or milestone.
- **Continuous Pipeline Progression:** When assigned a task, phase, or multi-step roadmap, execute sequentially and continuously through completion, running automated tests and reporting results.
- **No Halting Prompt Endings:** Do not conclude turns with questions such as:
  - "Shall I proceed to the next step?"
  - "May I have your permission to continue?"
  - "Would you like me to run the tests now?"
  - "Please confirm to proceed."
  - "Whenever you are ready, let me know..."
  - "Should I push these changes to git?"
  Instead, immediately proceed with execution and report verified outcomes.
- **Non-Blocking Planning Protocol:** When creating or updating plan artifacts (`implementation_plan.md`), never set `RequestFeedback: true` unless the user explicitly requests an interactive design pause or confirmation modal.

## 2. Platform Reliability & Clinical Integrity
- **Zero Circular Oscillation ("No Wheel-Spinning"):** Strictly prohibit repetitive re-auditing or endless discussion. Deliver concrete code, schemas, and passing test gates.
- **Maintain 100% Test Pass Rate:** Every phase must pass all pytests with exit code 0.
- **Strict Documentation Integrity:** Preserve all existing clinical and architectural guidelines; all roadmap additions must be strictly additive.
