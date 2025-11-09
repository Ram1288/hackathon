# AI-FIRST DEVELOPMENT GUIDELINES
**CRITICAL**: Read this before implementing ANY feature

## Core Philosophy

### ❌ NEVER DO THIS (Legacy/Hardcoded Approach)
```python
# WRONG: Hardcoded command patterns
if 'delete non-running pods' in query:
    return "kubectl delete pods --field-selector status.phase=Failed"

# WRONG: Hardcoded examples in prompts
prompt = """
Example: For 'delete failed pods':
  kubectl delete pods --field-selector status.phase=Failed
"""

# WRONG: Pattern-based fallbacks
if has_placeholder:
    cmd = cmd.replace('<pod-name>', 'actual-pod-name')  # NO!
```

### ✅ ALWAYS DO THIS (AI-First Approach)
```python
# RIGHT: Let LLM generate from training knowledge
prompt = """
Use your kubectl expertise to generate executable commands.
No placeholders. No examples needed.
"""

# RIGHT: LLM self-correction
if has_placeholder:
    refined = ask_llm_to_fix(commands)  # Let AI reason

# RIGHT: Safe filtering as last resort
if still_has_placeholder:
    return filter_unsafe_commands()  # Remove, don't replace
```

---

## Golden Rules

### Rule 1: Trust the AI
- **LLMs are trained on kubectl/helm documentation**
- They KNOW how to use `--field-selector`, `-l`, `--all-namespaces`
- Don't insult the AI by providing examples it already knows

### Rule 2: Principles, Not Examples
```python
# ❌ BAD: Prescriptive
"For failed pods: kubectl get pods --field-selector status.phase=Failed"

# ✅ GOOD: Principle-based
"For bulk operations: use --field-selector or -l (labels)"
```

### Rule 3: Self-Correction > Hardcoding
```
Flow:
1. LLM generates (might have errors)
2. Detect issues (regex/validation)
3. Ask LLM to self-correct (no examples!)
4. If still broken → filter safely (don't hardcode fix)
```

### Rule 4: Fail Safely
```python
# ❌ BAD: Hardcoded fallback
if refinement_fails:
    return hardcoded_command_pattern()

# ✅ GOOD: Safe failure
if refinement_fails:
    return filter_placeholders()  # Return only safe commands
    # If empty → user must rephrase (AI way)
```

---

## Implementation Checklist

Before writing ANY code, ask:

### ✅ Is this AI-driven?
- [ ] Does it rely on LLM reasoning?
- [ ] Are prompts principle-based (not example-based)?
- [ ] Does it use dynamic knowledge discovery?

### ✅ No hardcoded patterns?
- [ ] Zero hardcoded kubectl/helm commands
- [ ] No `if/else` based on query keywords
- [ ] No pattern matching → command mapping

### ✅ Self-correction enabled?
- [ ] Detects LLM errors (placeholders, invalid JSON)
- [ ] Asks LLM to fix (not manually)
- [ ] Filters safely if AI can't fix

### ✅ Discoverable knowledge?
- [ ] Learns from `kubectl --help`, not hardcoded docs
- [ ] Discovers available commands at runtime
- [ ] Stores learnings (not hardcoded patterns)

---

## Anti-Patterns to Avoid

### 1. Example Pollution
```python
# ❌ NEVER include command examples in prompts
prompt = """
For "delete failed pods":
  WRONG: kubectl delete pod <pod-name>
  CORRECT: kubectl delete pods --field-selector status.phase=Failed

For "list non-running":
  CORRECT: kubectl get pods --field-selector status.phase!=Running
"""
# This defeats the purpose of AI!
```

**Why it's bad:**
- LLM already knows this from training
- Creates rigid patterns
- Limits AI creativity
- Makes system fragile

**AI-First alternative:**
```python
prompt = """
Use your kubectl expertise. Commands must be immediately executable.
For bulk operations: --field-selector or -l labels.
"""
```

### 2. Hardcoded Fallbacks
```python
# ❌ NEVER hardcode command replacements
def fix_placeholder(cmd, query):
    if 'failed' in query:
        return "kubectl get pods --field-selector status.phase=Failed"
    if 'not running' in query:
        return "kubectl get pods --field-selector status.phase!=Running"
```

**AI-First alternative:**
```python
def fix_placeholder(cmd, query):
    # Ask LLM to reason about the fix
    return llm_refine(cmd, query)  # No hardcoding!
```

### 3. Keyword Matching
```python
# ❌ NEVER use keyword → command mapping
command_map = {
    'delete failed pods': 'kubectl delete pods --field-selector status.phase=Failed',
    'restart deployment': 'kubectl rollout restart deployment {name}',
}
```

**AI-First alternative:**
```python
# Let LLM generate based on semantic understanding
commands = llm.generate_commands(user_query)
```

### 4. Overly Aggressive Validation
```python
# ❌ BAD: Treating valid K8s values as placeholders
if re.search(r'[A-Z_]{3,}', cmd):
    reject(cmd)  # FALSE POSITIVE: Rejects "status.phase=Failed"!
```

**Why it's bad:**
- False positives block valid commands
- Kubernetes uses PascalCase/UPPERCASE enums: `Failed`, `Running`, `Unknown`, `CrashLoopBackOff`
- JSONPath uses uppercase: `{.items[*].metadata.name}`
- Flags have uppercase: `--field-selector STATUS=Running`

**AI-First alternative:**
```python
# ✅ GOOD: Whitelist valid K8s terms, only block OBVIOUS placeholders
valid_k8s_terms = ['Failed', 'Running', 'Unknown', 'Succeeded', 'Pending', 'Error']
obvious_placeholders = ['<pod-name>', 'POD_NAME', '$RELEASE', '{namespace}']

# Only reject if it has placeholders AND not a valid K8s enum
if has_placeholder(cmd) and not contains_valid_k8s_term(cmd):
    reject(cmd)
```

---

## Testing AI-First Systems

### Good Test
```python
def test_ai_command_generation():
    """LLM should generate correct commands without examples"""
    query = "delete pods that are not running"
    commands = llm_agent.generate_action_commands(query, namespace="test")
    
    # Verify: no placeholders
    assert not has_placeholders(commands)
    
    # Verify: uses field-selector (AI knows this)
    assert '--field-selector' in commands[0]['cmd']
```

### Bad Test
```python
def test_command_generation():
    """Expects exact hardcoded command"""
    query = "delete failed pods"
    cmd = get_command(query)
    
    # ❌ This forces hardcoding!
    assert cmd == "kubectl delete pods --field-selector status.phase=Failed"
```

---

## When to Break These Rules

**NEVER.** If you think you need to hardcode:

1. **Question**: Can LLM do this with better prompting?
2. **If stuck**: Ask LLM to refine (don't hardcode)
3. **If broken**: Filter safely (return empty, ask user to rephrase)

**Remember**: Hardcoding ONE example starts the slippery slope back to legacy systems.

---

## Code Review Checklist

Reject PR if it contains:
- [ ] Hardcoded kubectl/helm commands
- [ ] Command examples in prompts
- [ ] Keyword → command mappings
- [ ] Pattern-based fallbacks with hardcoded replacements
- [ ] `if/else` chains based on query keywords

Approve PR if it uses:
- [ ] LLM reasoning for all logic
- [ ] Principle-based prompts
- [ ] Self-correction loops
- [ ] Safe filtering (no hardcoded alternatives)
- [ ] Dynamic knowledge discovery

---

## Success Metrics

### ❌ Legacy System
- Developer adds 50 lines of code for each new query type
- Maintains 500+ lines of command patterns
- Breaks when Kubernetes API changes
- Can't handle creative queries

### ✅ AI-First System
- Developer adds 0 lines for new query types
- Maintains <100 lines of principle prompts
- Adapts automatically to API changes
- Handles creative queries naturally

---

## Emergency Procedure

If you catch yourself typing:
```python
if 'delete' in query and 'failed' in query:
    return "kubectl delete pods --field-selector..."
```

**STOP. DO THIS INSTEAD:**
1. Delete that code
2. Improve the LLM prompt with better principles
3. Add self-correction logic
4. Test with LLM reasoning
5. Document the learning (not the pattern)

---

## Final Word

**The moment you hardcode ONE command, you've lost the AI-first battle.**

Every hardcoded pattern is:
- A failure of trust in AI
- A maintenance burden
- A limitation on creativity
- A step back to legacy systems

**Stay AI-first. Always.**

---

## Lessons Learned (Real Examples)

### Issue #1: False Positive Placeholder Detection
**Date**: 2025-01-09  
**Problem**: Regex `r'\b[A-Z_]{3,}\b'` flagged valid kubectl commands as placeholders  
**Example**: `status.phase=Failed` was treated as placeholder because "Failed" matched uppercase pattern  
**Impact**: Valid commands blocked unnecessarily, triggered unnecessary LLM refinement  
**Root Cause**: Validation logic didn't distinguish between K8s enum values and actual placeholders  

**Solution** (AI-First):
```python
# ✅ Whitelist valid K8s terms
valid_k8s_terms = r'\b(Failed|Running|Unknown|Succeeded|Pending|Error)\b'

# Only flag OBVIOUS placeholders
obvious_placeholders = [
    r'<[^>]+>',           # <pod-name>
    r'\$[A-Z_][A-Z_0-9]*', # $POD_NAME
    r'\bPOD_NAME\b',      # POD_NAME (literal)
]

# Don't use generic uppercase pattern - too many false positives
```

**Lesson**: Trust K8s API values. Don't over-validate. Kubernetes legitimately uses uppercase enums.

---

### Issue #2: LLM Generated Wrong Command (Wrong Status Phase)
**Date**: 2025-01-09  
**Problem**: Query "delete pods not running" → LLM generated `--field-selector status.phase=Failed`  
**Reality**: "Not running" means ANY phase except Running (Failed, Succeeded, Unknown, Pending, etc.)  
**Impact**: Command only deleted Failed pods, ignored Succeeded/Unknown/Pending pods  

**Root Cause**: LLM made semantic assumption without understanding full requirement
- LLM interpreted "not running" → "failed" (too narrow)
- Correct interpretation: "not running" → "phase != Running" (includes ALL non-running states)

**Why This Happened**:
- Prompt didn't provide semantic clarity about K8s pod phases
- LLM used common language interpretation, not K8s API logic
- No guidance on phase vs container status distinction

**Kubernetes Reality**:
- **Pod Phases**: Pending, Running, Succeeded, Failed, Unknown
- **Container Statuses**: Waiting, Running, Terminated (with reasons like CreateContainerConfigError)
- Pod can be "Running" phase but have container errors (CreateContainerConfigError, CrashLoopBackOff)
- **Pod can be "Pending" phase but have CreateContainerConfigError (NOT RUNNING but NOT Failed!)**

**Real Example** (User's actual case):
```bash
$ oc get pods -n nm-cal-observability
NAME                                READY   STATUS                       RESTARTS   AGE
grafana-operator-7894f4648f-dq7b7   0/1     CreateContainerConfigError   0          8m5s

$ kubectl describe pod grafana-operator-7894f4648f-dq7b7
Status:           Pending  # ← NOT Failed!
State:            Waiting
  Reason:         CreateContainerConfigError
Events:
  Warning  Failed  Error: container has runAsNonRoot and image will run as root
```

**What LLM Did** (WRONG):
```bash
# ❌ Only checked Failed phase - MISSED the Pending pods with errors!
kubectl get pods --field-selector=status.phase=Failed
```

**What LLM Should Do** (CORRECT):
```bash
# ✅ First: Get ALL pods and check STATUS column (shows real state)
kubectl get pods -n nm-cal-observability

# ✅ Then: Describe pods where READY != 1/1
kubectl get pods -n nm-cal-observability -o json | \
  jq -r '.items[] | select(.status.containerStatuses[]?.ready == false) | .metadata.name' | \
  xargs kubectl describe pod -n nm-cal-observability

# ✅ Or simply: Check all non-Running phases
kubectl get pods --field-selector='status.phase!=Running' -n nm-cal-observability
```

**Wrong Interpretation** (what LLM did):
```bash
# ❌ Only deletes Failed pods (misses Succeeded, Unknown, Pending)
kubectl delete pods --field-selector status.phase=Failed
```

**Correct Interpretation**:
```bash
# ✅ Deletes ALL non-Running pods
kubectl get pods --field-selector status.phase!=Running -o name | xargs kubectl delete

# Or more explicit:
kubectl delete pods --field-selector 'status.phase in (Failed,Succeeded,Unknown,Pending)'
```

**AI-First Solution**: Don't hardcode examples. Instead, add **SEMANTIC UNDERSTANDING** to prompt:
```python
prompt = """
**SEMANTIC UNDERSTANDING (CRITICAL):**
- "not running" = ANY status except Running (Failed, Succeeded, Unknown, Pending, etc.)
- "failed" = Only Failed phase
- "completed" = Only Succeeded phase
- "errors" = Container status, not pod phase

**KUBERNETES POD PHASES:**
- Running: Pod is running (but containers may have errors!)
- Pending: Pod accepted but not started
- Succeeded: All containers terminated successfully
- Failed: All containers terminated, at least one failed
- Unknown: Pod state unknown
"""
```

**Why AI-First Wins**:
- LLM learns correct K8s semantics (applies to all future queries)
- No hardcoding of specific commands
- Works for variations: "not running", "non-running", "stopped", etc.
- LLM can reason about edge cases

**Lesson**: Natural language is ambiguous. Provide domain-specific semantic mappings in prompts, not command examples.

---

### Issue #4: Status Object is the Source of Truth
**Date**: 2025-01-09  
**Problem**: LLM filtered by phase, missed the real operational state in status object  
**User Insight**: "pod status will help us to determine better"  
**Breakthrough**: Status object contains complete truth - phase is just metadata  

**The Status Object Structure**:
```yaml
status:
  phase: Pending  # ← Superficial metadata
  conditions:     # ← THE TRUTH
    - type: Ready
      status: "False"  # ← Pod NOT ready (boolean fact)
      reason: ContainersNotReady  # ← Why not ready
      message: "containers with unready status: [grafana-operator]"
  containerStatuses:  # ← ROOT CAUSE
    - name: grafana-operator
      ready: false  # ← Container NOT ready
      state:
        waiting:
          reason: CreateContainerConfigError  # ← EXACT PROBLEM
          message: "runAsNonRoot and image will run as root"  # ← SOLUTION
```

**The Truth Hierarchy**:
1. **status.containerStatuses[].ready** = Is it working? (boolean)
2. **status.containerStatuses[].state.waiting.reason** = Why not? (root cause)
3. **status.conditions[type=Ready].reason** = Higher-level summary
4. **status.phase** = Least specific, almost irrelevant for debugging

**Old Approach** (WRONG):
```python
# ❌ Filter by phase - misses status object truth
prompt = "Check status.phase=Failed"
# Result: Missed Pending pods with CreateContainerConfigError!
```

**AI-First Approach** (CORRECT):
```python
# ✅ Teach status object structure (applies to ALL K8s resources)
prompt = """
**STATUS STRUCTURE WISDOM:**
- status.conditions[] = condition type, status (True/False), reason, message
- status.containerStatuses[] = ready (boolean), state.waiting.reason (root cause)
- Phase is metadata - status object is truth

For "not running" → status.conditions[type=Ready].status == False
For root cause → status.containerStatuses[].state.waiting.reason
"""
```

**Universal Pattern** (Applies to ALL resources):
- **Deployment**: status.conditions[type=Available], readyReplicas vs replicas
- **StatefulSet**: status.currentReplicas vs readyReplicas
- **DaemonSet**: status.numberReady vs desiredNumberScheduled
- **Job**: status.conditions[type=Complete/Failed], succeeded/failed
- **CronJob**: status.lastScheduleTime, status.active[]

**Why AI-First Wins**:
- One concept (status object structure) works for ALL K8s resources
- LLM learns pattern, applies everywhere (Pods, Deployments, Jobs, etc.)
- No hardcoded resource-specific commands
- Scalable: works for future K8s resources automatically

**Lesson**: 
- Don't teach resource-specific commands
- Teach universal K8s patterns (status object structure)
- Phase is superficial - status object contains operational truth
- One conceptual pattern > infinite command examples

**Critical Technical Detail**:
- Human-formatted output = NO status object structure (overview + events)
- Structured output (JSON/YAML) = COMPLETE status object (all fields)
- For status.conditions[] or containerStatuses[] → Need structured format
- For quick overview with events → Human format sufficient
- LLM knows kubectl syntax - just teach when to use which format type

---

### Issue #3: LLM JSON Parsing Failed (Unescaped Quotes)
**Date**: 2025-01-09  
**Problem**: LLM generated valid kubectl command but invalid JSON  
**Example**: `"cmd": "jq ".items[]""` (nested quotes broke JSON parsing)  
**Impact**: AgentProcessingError, no commands executed  
**Root Cause**: LLM didn't escape quotes inside command strings  

**Bad Solution** (Legacy Way):
```python
# ❌ Hardcode quote escaping in post-processing
json_str = json_str.replace('jq "', 'jq \\"')  # Fragile!
json_str = json_str.replace('" |', '\\" |')   # Breaks valid cases!
```

**AI-First Solution**:
```python
# ✅ Teach LLM proper JSON formatting in prompt
prompt = """
**JSON FORMATTING RULES:**
- Use single quotes for shell/jq filters to avoid escaping
- GOOD: "kubectl get pods -o json | jq '.items[]'"
- BAD: "kubectl get pods -o json | jq ".items[]"" (breaks JSON!)
"""
```

**Why AI-First Wins**:
- LLM learns correct format (doesn't repeat mistake)
- Works for ALL future commands (not just jq)
- No fragile regex post-processing
- Cleaner, more maintainable code

**Lesson**: When LLM makes formatting mistakes, improve the prompt (teach), don't patch the output (fix).

---

### Issue #5: Universal Debugging Pattern for ALL K8s Resources
**Date**: 2025-11-09  
**Problem**: Debugging logic was hardcoded for specific resource types (pods, deployments)  
**User Insight**: "for any resource type debugging. we can describe the resource and check for the events and pass only error details for analysis. or check for respective resource pods logs for error details"  
**Breakthrough**: Universal pattern works for ALL K8s resources - no need for resource-specific logic!  

**The Universal Debugging Pattern**:

```yaml
# Works for: pods, deployments, services, statefulsets, daemonsets, replicasets, 
#            configmaps, secrets, ingress, persistentvolumeclaims, etc.

Step 1: kubectl describe <resource-type> <name> -n <namespace>
  ↓
  Gets: Status, Conditions, Events (chronological error timeline)
  
Step 2 (if resource manages pods): Check pod logs
  - Pod → kubectl logs <pod-name>
  - Deployment/StatefulSet/DaemonSet/ReplicaSet → kubectl logs -l app=<name>
  - Service → describe service → find endpoints → find pods → kubectl logs
```

**Why This Pattern is Universal**:
1. **ALL K8s resources have Events** when something goes wrong
2. **Events are chronological** - show what the system attempted
3. **Events contain error messages** from controllers/schedulers/kubelet
4. **Logs supplement Events** with application-level details
5. **Pattern is identical** for ALL resource types

**Example: Debugging Different Resources**:

```bash
# Debug Pod
kubectl describe pod my-pod -n default     # → Events show why it failed
kubectl logs my-pod -n default             # → Application errors

# Debug Deployment
kubectl describe deployment my-app -n default  # → Events show scaling/rollout issues
kubectl logs -l app=my-app -n default --prefix # → Pod logs from deployment

# Debug Service
kubectl describe service my-svc -n default     # → Events show endpoint issues
kubectl get endpoints my-svc -n default        # → Find backend pods
kubectl logs <backend-pod> -n default          # → Check pod logs

# Debug StatefulSet
kubectl describe statefulset db -n default     # → Events show pod creation issues
kubectl logs -l app=db -n default --prefix     # → Logs from stateful pods

# Debug ConfigMap (yes, even ConfigMaps!)
kubectl describe configmap app-config -n default  # → Events show mount failures
```

**Old Approach** (WRONG):
```python
# ❌ Resource-specific hardcoded logic
if resource_type == 'pod':
    run_describe_pod()
    run_logs_pod()
elif resource_type == 'deployment':
    run_describe_deployment()
    run_get_pods_from_deployment()
elif resource_type == 'service':
    # ... different logic
# Each resource type needs custom code!
```

**AI-First Approach** (CORRECT):
```python
# ✅ Teach universal pattern in prompt
prompt = """
**UNIVERSAL DEBUGGING PATTERN (Works for ANY K8s Resource):**

1. **Describe the Resource** → Get Events and Error Details
   - kubectl describe <resource-type> <name> -n <namespace>
   - Events section contains THE TRUTH: why it failed, what went wrong
   - Works for: pods, deployments, services, statefulsets, daemonsets, etc.

2. **Check Associated Pod Logs** (if resource manages pods)
   - Resources that manage pods: deployments, statefulsets, daemonsets, replicasets
   - Pattern: Resource → Pods → Logs

3. **Filter Events for Errors Only**
   - From describe output: look for type=Warning or type=Error
   - Pass only error details for LLM analysis (not entire describe output)
"""

# ✅ Investigation agent auto-detects resource type, applies universal pattern
def investigate_resource(resource_type, resource_name, namespace):
    # Step 1: ALWAYS describe (works for ALL resources)
    describe_output = kubectl_describe(resource_type, resource_name, namespace)
    
    # Step 2: If resource manages pods, get logs
    if resource_type in ['deployment', 'statefulset', 'daemonset', 'replicaset']:
        pod_logs = kubectl_logs_by_label(f"app={resource_name}", namespace)
    elif resource_type == 'pod':
        pod_logs = kubectl_logs(resource_name, namespace)
    
    # No resource-specific logic needed!
```

**Why AI-First Wins**:
- **Single universal pattern** replaces infinite resource-specific code
- **Auto-detects resource type** from kubectl output (no hardcoding)
- **Scales to future K8s resources** (CRDs, new resource types)
- **LLM understands Events** - can extract error details automatically
- **No maintenance burden** when K8s adds new resources

**Key Insight**: 
- Events are the **universal debugging interface** in Kubernetes
- ALL resources emit Events to explain state transitions and errors
- One pattern to rule them all: `kubectl describe` → Events → Errors
- Logs are supplementary (only for resources that manage pods)

**Lesson**: 
- Don't write resource-specific debugging logic
- Teach ONE universal pattern that works for ALL resources
- K8s already provides universal interface (Events) - use it!
- Resource-agnostic code is more maintainable and scalable

---

## Version History
- v1.0 (2025-01-09): Initial AI-first guidelines
- v1.1 (2025-01-09): Added Anti-Pattern #4 (Overly Aggressive Validation)
- v1.2 (2025-01-09): Added Lessons Learned section with real examples
- v1.3 (2025-01-09): Added Issue #3 (JSON parsing with unescaped quotes)
- v1.4 (2025-11-09): Added Issue #5 (Universal debugging pattern for all K8s resources)
- Reviewed by: AI Architecture Team
- Status: **MANDATORY - NO EXCEPTIONS**

