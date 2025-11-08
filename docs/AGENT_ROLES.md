# Agent Roles and Responsibilities

## Overview
DevDebug AI uses multiple specialized agents working together. Here's what each does:

## Core Agents

### 1. **DocumentAgent** (`document_agent.py`)
- **Role:** RAG (Retrieval Augmented Generation) - finds relevant documentation
- **Purpose:** Searches knowledge base for relevant K8s documentation and examples
- **Input:** User query
- **Output:** Relevant docs, code examples, patterns

### 2. **ExecutionAgent** (`execution_agent.py`)
- **Role:** Command execution with security
- **Purpose:** Executes kubectl commands safely
- **Input:** Commands to execute (from LLM or Investigation Agent)
- **Output:** Command results (stdout, stderr, status)

### 3. **LLMAgent** (`llm_agent.py`)
- **Role:** AI reasoning and analysis
- **Purpose:** 
  - Generates kubectl commands based on query
  - Analyzes diagnostic results
  - Provides comprehensive solutions
- **Input:** Query + context (docs, diagnostics, learned patterns)
- **Output:** Commands or analysis text

### 4. **KnowledgeAgent** (`knowledge_agent.py`)
- **Role:** Dynamic environment discovery and learning
- **Purpose:**
  - Discovers available K8s resources (`kubectl api-resources`)
  - Discovers command capabilities (`kubectl --help`)
  - Learns from successful troubleshooting sessions
  - Builds pattern knowledge over time
- **Input:** Environment queries, successful resolutions
- **Output:** Discovered capabilities, learned patterns

### 5. **SecurityPolicyAgent** (`security_policy_agent.py`)
- **Role:** AI-driven command safety evaluation
- **Purpose:**
  - Evaluates if commands are safe to execute
  - Reasons about command intent vs user query
  - Provides security recommendations
- **Input:** Command + user query + permissions
- **Output:** Safe/unsafe + reason + suggestions

## Investigation Agents (Work Together)

### 6. **InvestigatorAgent** (`investigator_agent.py`)
- **Role:** Pattern recognition and analysis
- **Purpose:**
  - Analyzes diagnostic results for common error patterns
  - Detects root cause indicators (certificate expired, OOM, etc.)
  - Determines if more investigation needed
  - Suggests next diagnostic steps
- **Input:** Diagnostic results (kubectl output)
- **Output:** Findings, patterns detected, next steps needed
- **Key Method:** `analyze_diagnostic_results(diagnostics)` → findings

### 7. **InvestigationAgent** (`investigation_agent.py`)
- **Role:** Iterative AI-driven troubleshooting orchestrator
- **Purpose:**
  - Runs multiple investigation iterations
  - Uses LLM to generate commands
  - Uses InvestigatorAgent to analyze results
  - Continues until root cause found or max iterations
  - Builds hypothesis and confidence score
- **Input:** Initial query, namespace, pod name
- **Output:** Investigation result with root cause, solution, all findings
- **Key Method:** `investigate(query, namespace, pod_name)` → full investigation result
- **Dependencies:** Needs LLMAgent and ExecutionAgent

## How They Work Together

### Investigation Flow:
```
User Query
    ↓
DocumentAgent → finds relevant docs
    ↓
InvestigationAgent.investigate():
    ├─→ LLMAgent: generate diagnostic commands
    ├─→ ExecutionAgent: run commands
    ├─→ InvestigatorAgent: analyze results, detect patterns
    ├─→ Decision: Root cause found? 
    │       Yes → Stop, return solution
    │       No → Generate follow-up commands, iterate (max 5 times)
    ↓
LLMAgent: final comprehensive solution
    ↓
User sees: Root cause + solution + investigation path
```

### Key Difference:
- **InvestigatorAgent** = Analyzes single diagnostic result → finds patterns
- **InvestigationAgent** = Orchestrates full investigation → iterates until solved

## Example:

**Query:** "Pod keeps restarting"

1. **DocumentAgent:** Finds CrashLoopBackOff docs
2. **InvestigationAgent** starts investigation:
   - **Iteration 1:**
     - **LLMAgent:** "Generate: kubectl describe pod, kubectl logs"
     - **ExecutionAgent:** Runs commands
     - **InvestigatorAgent:** Analyzes → "Found: Exit Code 137 (OOMKilled pattern)"
     - **Decision:** Need more info about memory
   - **Iteration 2:**
     - **LLMAgent:** "Generate: kubectl top pod, kubectl get pod -o yaml"
     - **ExecutionAgent:** Runs commands
     - **InvestigatorAgent:** Analyzes → "Found: Memory limit 128Mi, using 200Mi"
     - **Decision:** ROOT CAUSE FOUND! (confidence: 0.95)
3. **LLMAgent:** Generates comprehensive solution: "Increase memory limit to 256Mi"
4. **User sees:** 
   - Root cause: OOM due to insufficient memory limit
   - Solution: Update deployment memory limits
   - Investigation path: describe → logs → top → yaml (2 iterations)

## Configuration

Both agents configured in `config/config.yaml`:

```yaml
investigator_agent:
  enabled: true
  # Pattern recognition settings

investigation_agent:
  enabled: true
  max_iterations: 5
  min_confidence: 0.7
  # Iterative investigation settings
```

## Summary

- **InvestigatorAgent** = Smart pattern detector (analyzes what you have)
- **InvestigationAgent** = Persistent investigator (keeps digging until solved)
- Together they provide **iterative AI-driven troubleshooting** instead of one-shot diagnostics
