# AI-Driven Dynamic Diagnostic Command Generation

## Overview

DevDebug AI now uses **AI to dynamically decide which kubectl commands to run** based on your natural language query, instead of relying on hardcoded templates.

## Problem Solved

### Before (Template-Based):
```
User: "ccr-harbor-jobservice restarted 3 times, what's the cause?"
System: 
  - Checks if "pod" in query → runs kubectl get pods ✓
  - Checks if "restart" in query → No template match ✗
  - Misses: kubectl describe, kubectl logs --previous, kubectl get events
Result: Incomplete diagnostics
```

### After (AI-Driven):
```
User: "ccr-harbor-jobservice restarted 3 times, what's the cause?"
LLM: Analyzes query and generates:
  1. kubectl describe pod ccr-harbor-jobservice -n cal-shared-product
  2. kubectl logs ccr-harbor-jobservice -n cal-shared-product --previous
  3. kubectl logs ccr-harbor-jobservice -n cal-shared-product  
  4. kubectl get events -n cal-shared-product --field-selector involvedObject.name=ccr-harbor-jobservice
Result: Complete diagnostics with root cause identified
```

## How It Works

### Architecture

```
User Query
    ↓
📚 Step 1: RAG - Search Documentation
    ↓
🤖 Step 2: AI Command Generation
    ├─ LLM Available? → Generate smart commands via Ollama
    └─ LLM Unavailable? → Use intelligent fallback
    ↓
🔒 Step 3: Security Validation
    ├─ Whitelist check (only get, describe, logs, top allowed)
    ├─ Blacklist check (block delete, apply, edit, etc.)
    └─ Permission check (allow_create, allow_update, allow_delete flags)
    ↓
▶️  Step 4: Execute Commands
    ↓
🤖 Step 5: LLM Analysis
    └─ Analyze results and provide root cause + solution
```

### Example Scenarios

#### Scenario 1: Pod Restart Investigation
```yaml
Query: "grafana-operator pod keeps restarting, why?"

AI Generates:
  - kubectl describe pod grafana-operator-xxx -n namespace
  - kubectl logs grafana-operator-xxx -n namespace --previous  # Previous crash logs
  - kubectl logs grafana-operator-xxx -n namespace             # Current logs
  - kubectl get events -n namespace --field-selector involvedObject.name=grafana-operator-xxx

Why Smart: Automatically adds --previous flag for crash logs
```

#### Scenario 2: Resource Listing
```yaml
Query: "describe the pods in nm-cal-observability"

AI Generates:
  - kubectl get pods -n nm-cal-observability              # List first
  - kubectl get pods -n nm-cal-observability -o wide      # Detailed view

Why Smart: Recognizes "describe" intent and lists pods for overview
```

#### Scenario 3: Error Investigation
```yaml
Query: "CreateContainerConfigError in grafana-operator, what's wrong?"

AI Generates:
  - kubectl describe pod grafana-operator-xxx -n namespace  # Get config details
  - kubectl get events -n namespace --sort-by='.lastTimestamp'  # Recent events
  - kubectl logs grafana-operator-xxx -n namespace         # Application logs
  - kubectl get configmaps -n namespace                    # Check config resources

Why Smart: Knows ConfigError needs configmap inspection
```

## Configuration

### Enable/Disable AI-Driven Mode

**config.yaml:**
```yaml
orchestrator:
  ai_driven_diagnostics: true  # Use AI (default)
  # ai_driven_diagnostics: false  # Use templates only
```

### Security Settings

All AI-generated commands go through security validation:

```yaml
execution_agent:
  read_only_mode: true          # Only allow safe read operations (default)
  allow_create: false           # Block kubectl create/apply
  allow_update: false           # Block kubectl edit/patch/scale
  allow_delete: false           # Block kubectl delete
```

## Fallback Behavior

When Ollama LLM is unavailable, the system uses intelligent rule-based fallback:

### Fallback Logic
```python
if "describe" in query:
    if "pod" in query:
        → kubectl get pods + kubectl get pods -o wide
    elif "node" in query:
        → kubectl describe nodes
    elif "namespace" in query:
        → kubectl describe namespace {name}

elif pod_name and "restart|crash|error" in query:
    → kubectl describe pod {pod}
    → kubectl logs {pod} --previous
    → kubectl logs {pod}
    → kubectl get events --field-selector involvedObject.name={pod}

elif "namespace" in query:
    → kubectl get namespaces

else:
    → kubectl get pods -n {namespace} -o wide  # Safe default
```

## Benefits

### For Users
✅ **Natural language** - Ask questions how you naturally think  
✅ **Complete diagnostics** - Gets all relevant info in one go  
✅ **Time saving** - No need to run multiple commands manually  
✅ **Learn as you go** - See which commands the AI chose and why  

### For Developers
✅ **Zero maintenance** - No need to add templates for new scenarios  
✅ **AI adapts** - Handles edge cases automatically  
✅ **Extensible** - Works with any kubectl-compatible cluster  
✅ **Secure by default** - All commands validated  

## Comparison: Template vs AI

| Aspect | Template-Based | AI-Driven |
|--------|---------------|-----------|
| **Flexibility** | Fixed patterns only | Adapts to any query |
| **Maintenance** | Add code for each new case | Zero code changes needed |
| **Coverage** | ~20 predefined scenarios | Unlimited scenarios |
| **Context awareness** | Simple keyword matching | Understands intent |
| **Pod name extraction** | Must be provided explicitly | Extracts from natural language |
| **Command optimization** | May run unnecessary commands | Only runs what's needed |
| **Security** | Template-based validation | Same whitelist + blacklist |

## Real-World Examples

### Example 1: Memory Issue
```
❌ Old: "pod using too much memory"
   → kubectl get pods
   → User has to manually run: kubectl top pods, kubectl describe pod

✅ New: "pod using too much memory"  
   → kubectl top pods -n {namespace}
   → kubectl describe pod {pod} (if specific pod mentioned)
   → kubectl get events (check for OOMKilled)
```

### Example 2: Network Issue
```
❌ Old: "service not reachable"
   → kubectl get pods (not helpful)
   → User manually runs: kubectl get svc, kubectl describe svc

✅ New: "service not reachable"
   → kubectl get svc -n {namespace}
   → kubectl describe svc {service}
   → kubectl get endpoints {service}
   → kubectl get pods -l app={selector}
```

### Example 3: Configuration Issue
```
❌ Old: "configmap not loading"
   → kubectl get pods (shows symptoms, not cause)

✅ New: "configmap not loading"
   → kubectl get configmaps -n {namespace}
   → kubectl describe configmap {name}
   → kubectl get pods -l app={selector}
   → kubectl describe pod {pod}
```

## Technical Implementation

### LLM Prompt Template
The AI uses a specialized prompt to generate commands:

```
You are a Kubernetes expert. Based on the user's query, generate
the EXACT kubectl commands needed to gather diagnostic information.

Rules:
1. Only READ-ONLY commands (get, describe, logs, top)
2. Include --previous flag for crash/restart queries
3. Include events for troubleshooting
4. Be specific with pod names
5. Maximum 5 commands

Output: JSON format with {cmd, reason}
```

### Security Pipeline
```python
AI Generated Command
    ↓
Whitelist Check (get, describe, logs, top, etc.)
    ↓
Blacklist Check (delete, apply, edit blocked)
    ↓
Permission Check (read_only_mode, allow_* flags)
    ↓
Execute or Block with helpful message
```

## Future Enhancements

Potential improvements for v2.0:

1. **Multi-round diagnostics** - If initial commands don't reveal issue, AI generates follow-up commands
2. **Cluster-specific learning** - Remember common issues in your cluster
3. **Performance optimization** - Cache similar query patterns
4. **Custom command templates** - Allow users to define their own command patterns
5. **Interactive mode** - Ask clarifying questions before generating commands

## Conclusion

The AI-driven diagnostic system transforms DevDebug from a **template-based tool** into a **truly intelligent assistant** that understands your troubleshooting intent and gathers exactly the information needed - automatically, securely, and efficiently.

**No more guesswork. No more manual command chaining. Just ask, and the AI figures out the rest.** 🚀
