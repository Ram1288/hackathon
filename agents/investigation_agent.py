"""
Iterative Investigation Agent
AI-driven iterative troubleshooting - keeps digging until root cause found
"""
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from core.interfaces import BaseAgent, AgentRequest, AgentResponse, AgentType, AgentProcessingError


@dataclass
class InvestigationStep:
    """Single step in investigation"""
    iteration: int
    commands_executed: List[str]
    findings: Dict[str, Any]
    hypothesis: str
    confidence: float  # 0.0 to 1.0
    needs_more_investigation: bool


class InvestigationAgent(BaseAgent):
    """
    Intelligent iterative investigation - AI decides when to stop
    NO hardcoded investigation paths - AI reasons about next steps
    """
    
    def initialize(self):
        """Initialize investigation agent"""
        self.agent_type = AgentType.EXECUTION
        self.max_iterations = self.config.get('max_investigation_iterations', 5)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.8)
        
        # Will be injected
        self.llm_agent = None
        self.execution_agent = None
    
    def set_agents(self, llm_agent, execution_agent):
        """Inject dependent agents"""
        self.llm_agent = llm_agent
        self.execution_agent = execution_agent
    
    def investigate(self, initial_query: str, namespace: str, pod_name: str = "") -> Dict:
        """
        Iteratively investigate until root cause found or max iterations reached.
        AI decides at each step: continue or stop.
        """
        investigation_history = []
        current_context = {
            'query': initial_query,
            'namespace': namespace,
            'pod_name': pod_name,
            'findings': {}
        }
        
        print(f"\n🔬 Starting AI-driven iterative investigation (max {self.max_iterations} iterations)...\n")
        
        for iteration in range(1, self.max_iterations + 1):
            print(f"{'='*80}")
            print(f"🔍 Investigation Iteration {iteration}/{self.max_iterations}")
            print(f"{'='*80}\n")
            
            # Step 1: Analyze current findings (even if partial)
            analysis = self._analyze_current_findings(current_context, investigation_history, iteration)
            
            print(f"📊 Current Hypothesis: {analysis['hypothesis']}")
            print(f"📈 Confidence: {analysis['confidence']*100:.1f}%")
            print(f"🎯 Root Cause Found: {'YES' if not analysis['needs_more_investigation'] else 'NO'}\n")
            
            # Step 2: Decide if we should continue
            if not analysis['needs_more_investigation']:
                print(f"✅ Root cause identified with {analysis['confidence']*100:.1f}% confidence!")
                print(f"🎉 Investigation complete in {iteration} iteration(s)\n")
                break
            
            if iteration == self.max_iterations:
                print(f"⚠️  Reached maximum iterations. Providing best analysis so far...\n")
                break
            
            # Step 3: Generate next investigation commands
            next_commands = self._generate_next_commands(analysis, current_context, iteration)
            
            if not next_commands:
                print(f"ℹ️  No further investigation commands needed.\n")
                break
            
            print(f"🔧 Executing {len(next_commands)} diagnostic command(s)...\n")
            
            # Step 4: Execute next round of diagnostics
            results = self._execute_investigation_commands(next_commands, namespace)
            
            # Step 5: Update context with new findings
            current_context['findings'].update(results)
            
            # Step 6: Record this investigation step
            step = InvestigationStep(
                iteration=iteration,
                commands_executed=next_commands,
                findings=results,
                hypothesis=analysis['hypothesis'],
                confidence=analysis['confidence'],
                needs_more_investigation=analysis['needs_more_investigation']
            )
            investigation_history.append(step)
            
            print(f"\n")
        
        # Final comprehensive analysis
        final_analysis = self._generate_final_report(investigation_history, current_context)
        
        return {
            'iterations': len(investigation_history),
            'final_hypothesis': final_analysis['root_cause'],
            'confidence': final_analysis['confidence'],
            'solution': final_analysis['solution'],
            'all_findings': current_context['findings'],
            'investigation_path': [
                {
                    'iteration': step.iteration,
                    'hypothesis': step.hypothesis,
                    'confidence': step.confidence
                }
                for step in investigation_history
            ]
        }
    
    def _analyze_current_findings(
        self, 
        context: Dict, 
        history: List[InvestigationStep],
        iteration: int
    ) -> Dict:
        """
        Analyze current findings to determine:
        1. What have we learned so far?
        2. What's the current hypothesis?
        3. How confident are we?
        4. Do we need more investigation?
        
        This works even if LLM is unavailable (pattern recognition from logs)
        """
        findings = context['findings']
        
        # CRITICAL: In iteration 1, we usually don't have detailed findings yet
        # Use pattern recognition which is more reliable than LLM speculation
        if iteration == 1 or not findings:
            return self._pattern_based_analysis(findings, context['query'])
        
        # In later iterations with actual data, try LLM analysis (if available)
        if self.llm_agent and self._check_llm_available():
            try:
                return self._llm_analyze_findings(context, history, iteration)
            except Exception as e:
                print(f"   ⚠️  LLM analysis failed: {e}, using pattern recognition...")
        
        # Fallback: Intelligent pattern recognition (still AI-like, not hardcoded keywords)
        return self._pattern_based_analysis(findings, context['query'])
    
    def _llm_analyze_findings(
        self, 
        context: Dict, 
        history: List[InvestigationStep],
        iteration: int
    ) -> Dict:
        """Use LLM to analyze findings intelligently"""
        
        prompt = f"""You are a Kubernetes troubleshooting expert conducting an iterative investigation.

**Original Problem:**
{context['query']}

**Investigation History:**
{self._format_investigation_history(history)}

**Current Findings:**
{self._format_findings(context['findings'])}

**Your Task:**
Analyze the findings and determine:
1. What is the ROOT CAUSE hypothesis based on current evidence?
2. How confident are you? (0.0 to 1.0)
3. Do we need MORE investigation or is the root cause clear?
4. If more investigation needed, what specific aspect should we explore?

**Output JSON:**
{{
  "hypothesis": "clear statement of suspected root cause",
  "confidence": 0.85,
  "needs_more_investigation": true/false,
  "reasoning": "why you believe this",
  "next_focus": "what to investigate next (if needs_more_investigation=true)"
}}"""
        
        try:
            response = self.llm_agent._query_ollama(prompt)
            
            # Parse JSON response
            import json
            import re
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group())
                return {
                    'hypothesis': analysis.get('hypothesis', 'Investigating...'),
                    'confidence': float(analysis.get('confidence', 0.5)),
                    'needs_more_investigation': analysis.get('needs_more_investigation', True),
                    'next_focus': analysis.get('next_focus', 'general diagnostics'),
                    'reasoning': analysis.get('reasoning', '')
                }
        except Exception as e:
            print(f"   ⚠️  LLM analysis error: {e}")
        
        # If LLM fails, fallback to pattern recognition
        return self._pattern_based_analysis(context['findings'], context['query'])
    
    def _pattern_based_analysis(self, findings: Dict, query: str) -> Dict:
        """
        Intelligent pattern recognition from diagnostic output.
        Detects common K8s error patterns and determines if we have enough info.
        """
        all_output = ""
        for cmd, result in findings.items():
            if isinstance(result, dict):
                all_output += result.get('stdout', '') + "\n"
                all_output += result.get('stderr', '') + "\n"
        
        all_output_lower = all_output.lower()
        
        # Phase 1: Check if we have resource discovery output
        has_pod_list = 'kubectl get pods' in ' '.join(findings.keys()).lower()
        has_detailed_info = any(cmd for cmd in findings.keys() if 'describe' in cmd.lower() or 'logs' in cmd.lower())
        
        # Detect error patterns (intelligent, not hardcoded)
        error_indicators = []
        confidence = 0.3  # Start low
        hypothesis = "Gathering diagnostic information..."
        needs_more = True
        
        # Look for specific K8s error patterns
        if 'createcontainerconfigerror' in all_output_lower:
            hypothesis = "Pods have CreateContainerConfigError - likely missing ConfigMap or Secret"
            confidence = 0.9  # High confidence on this specific error
            needs_more = not has_detailed_info  # Need detailed describe if we don't have it
        
        elif 'imagepullbackoff' in all_output_lower or 'errimagepull' in all_output_lower:
            hypothesis = "Pods cannot pull container images - check image name and registry credentials"
            confidence = 0.9
            needs_more = not has_detailed_info
        
        elif 'crashloopbackoff' in all_output_lower:
            hypothesis = "Pods are crash looping - need to examine logs for application error"
            confidence = 0.8
            needs_more = not has_detailed_info  # Need logs!
        
        elif 'oomkilled' in all_output_lower:
            hypothesis = "Pods killed due to Out of Memory - need to increase memory limits"
            confidence = 0.95
            needs_more = False  # Pretty clear what the issue is
        
        elif 'evicted' in all_output_lower:
            hypothesis = "Pods evicted - likely node resource pressure or PVC issues"
            confidence = 0.85
            needs_more = not has_detailed_info
        
        # Generic error detection
        elif not hypothesis.startswith("Gathering"):
            pass  # Keep previous specific hypothesis
        else:
            # Look for ERROR/FATAL/PANIC lines
            error_lines = [line for line in all_output.split('\n') 
                          if any(marker in line.lower() for marker in ['error', 'fatal', 'panic', 'failed', 'warning'])]
            
            if error_lines:
                # Found explicit errors
                error_indicators.extend(error_lines[:3])  # Top 3 errors
                confidence = 0.7
                
                # Extract the actual error message
                hypothesis = "Detected errors: " + "; ".join(
                    line.strip()[:100] for line in error_lines[:2]
                )
                
                # Check if error is definitive
                if any(term in all_output_lower for term in ['certificate', 'expired', 'connection refused', 'not found']):
                    confidence = 0.9
                    needs_more = not has_detailed_info
                else:
                    needs_more = True
            
            # Check restart patterns
            elif 'restart count:' in all_output_lower or 'restarts:' in all_output_lower:
                hypothesis = "Pod is restarting - need to check logs and events for root cause"
                confidence = 0.5
                needs_more = True
        
        # Determine next focus
        if has_pod_list and not has_detailed_info:
            next_focus = "get detailed pod description and logs"
        elif has_detailed_info:
            next_focus = "analyze error messages and determine solution"
        else:
            next_focus = "discover affected resources"
        
        return {
            'hypothesis': hypothesis,
            'confidence': confidence,
            'needs_more_investigation': needs_more,
            'next_focus': next_focus,
            'reasoning': f'Analyzed {len(findings)} command outputs, found specific patterns' if confidence > 0.7 else 'Initial discovery phase'
        }
    
    def _generate_next_commands(
        self, 
        analysis: Dict, 
        context: Dict,
        iteration: int
    ) -> List[str]:
        """
        AI decides what commands to run next based on current analysis.
        Adapts investigation path based on findings.
        NOW HANDLES TWO-PHASE approach: Discovery → Detailed Diagnostics
        """
        if not analysis['needs_more_investigation']:
            return []
        
        # PHASE 1 (Iteration 1): Discovery - find the resources
        if iteration == 1:
            # Generate discovery commands (no specific names needed)
            if self.llm_agent and self._check_llm_available():
                try:
                    commands_response = self.llm_agent.generate_diagnostic_commands(
                        query=context['query'],  # Original query
                        namespace=context['namespace'],
                        pod_name=''  # Don't know yet
                    )
                    
                    return [cmd['cmd'] for cmd in commands_response[:3]]  # Max 3 discovery commands
                except Exception as e:
                    print(f"   ⚠️  Could not generate AI commands: {e}")
            
            # Fallback discovery commands
            return [
                f"kubectl get pods -n {context['namespace']} --field-selector=status.phase!=Running -o wide",
                f"kubectl get events -n {context['namespace']} --sort-by=.lastTimestamp --field-selector=type=Warning"
            ]
        
        # PHASE 2 (Iteration 2+): Detailed diagnostics with discovered resource names
        else:
            # Extract resource names from previous findings
            discovered_resources = self._extract_resource_names_from_findings(context['findings'])
            
            if not discovered_resources:
                print(f"   ⚠️  No specific resources discovered in previous iteration")
                return []
            
            # Generate targeted diagnostics for discovered resources
            commands = []
            next_focus = analysis.get('next_focus', 'detailed diagnostics')
            
            # UNIVERSAL DEBUGGING PATTERN: Apply describe → events → logs pattern to ANY resource
            for resource in discovered_resources[:2]:  # Limit to first 2 resources
                resource_type = resource['type']  # 'pod', 'deployment', 'service', 'statefulset', etc.
                resource_name = resource['name']
                
                # Step 1: ALWAYS describe the resource (works for ALL K8s resources)
                # This gets Events and error details universally
                commands.append(f"kubectl describe {resource_type} {resource_name} -n {context['namespace']}")
                
                # Step 2: If resource manages pods, check pod logs
                if resource_type == 'pod':
                    # Direct pod: get logs
                    commands.append(f"kubectl logs {resource_name} -n {context['namespace']} --tail=50")
                elif resource_type in ['deployment', 'statefulset', 'daemonset', 'replicaset']:
                    # Resources that manage pods: find their pods first, then logs
                    # Get one representative pod's logs (enough for diagnosis)
                    commands.append(f"kubectl logs -l app={resource_name} -n {context['namespace']} --tail=30 --prefix")
            
            return commands[:4]  # Max 4 detailed commands
    
    def _extract_resource_names_from_findings(self, findings: Dict) -> List[Dict]:
        """
        Parse kubectl output to extract actual resource names.
        UNIVERSAL: Works for ANY K8s resource type, not just pods/deployments.
        """
        resources = []
        
        for cmd, result in findings.items():
            if not isinstance(result, dict):
                continue
            
            stdout = result.get('stdout', '')
            if not stdout:
                continue
            
            # Universal pattern: 'kubectl get <resource-type>' → parse output
            # Extract resource type from command
            import re
            get_match = re.search(r'kubectl get (\w+)', cmd)
            if not get_match:
                continue
            
            resource_type = get_match.group(1).lower()
            # Normalize plural forms: pods → pod, deployments → deployment
            resource_type_singular = resource_type.rstrip('s') if resource_type.endswith('s') else resource_type
            
            # Parse kubectl get output (standard format: NAME  READY  STATUS  ...)
            lines = stdout.strip().split('\n')
            if len(lines) <= 1:  # No data, just header
                continue
            
            for line in lines[1:]:  # Skip header
                parts = line.split()
                if not parts:
                    continue
                
                resource_name = parts[0]
                # STATUS is typically column 2 or 3 depending on resource type
                status = parts[2] if len(parts) > 2 else (parts[1] if len(parts) > 1 else 'Unknown')
                
                # Add all resources with non-healthy status
                # For pods: status != 'Running'
                # For deployments: could check READY column (e.g., "0/1")
                # For services: check endpoints availability
                # Universal heuristic: if it doesn't look healthy, investigate
                
                if resource_type_singular == 'pod':
                    # Only add non-running pods
                    if status.lower() not in ['running', 'succeeded']:
                        resources.append({
                            'type': resource_type_singular,
                            'name': resource_name,
                            'status': status
                        })
                else:
                    # For other resources, add all (LLM will decide what needs investigation)
                    resources.append({
                        'type': resource_type_singular,
                        'name': resource_name,
                        'status': status
                    })
        
        return resources
    
    def _fallback_next_commands(self, context: Dict, iteration: int) -> List[str]:
        """Basic progressive investigation when AI unavailable"""
        namespace = context['namespace']
        pod_name = context.get('pod_name', '')
        
        # Progressive investigation depth
        if iteration == 1 and pod_name:
            return [
                f"kubectl describe pod {pod_name} -n {namespace}",
                f"kubectl logs {pod_name} -n {namespace} --previous --tail=50",
            ]
        elif iteration == 2:
            return [
                f"kubectl get events -n {namespace} --sort-by=.lastTimestamp --limit=20",
            ]
        
        return []
    
    def _execute_investigation_commands(self, commands: List[str], namespace: str) -> Dict:
        """Execute investigation commands and return results"""
        results = {}
        
        for cmd in commands:
            print(f"   ▶ {cmd}")
            try:
                # Execute via execution agent
                import subprocess
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                results[cmd] = {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                }
                
                # Show intelligent preview based on command type
                if result.stdout:
                    preview = self._generate_preview(cmd, result.stdout)
                    print(f"      ✓ {preview}")
                
            except Exception as e:
                results[cmd] = {'error': str(e)}
                print(f"      ✗ Command failed: {e}")
        
        return results
    
    def _generate_final_report(self, history: List[InvestigationStep], context: Dict) -> Dict:
        """Generate final comprehensive analysis"""
        
        if not history:
            return {
                'root_cause': 'Investigation incomplete',
                'confidence': 0.0,
                'solution': 'Unable to determine root cause'
            }
        
        # Get latest analysis
        latest = history[-1]
        
        # Try to generate solution with LLM
        if self.llm_agent and self._check_llm_available():
            try:
                solution_prompt = f"""Based on the investigation:

**Original Problem:** {context['query']}

**Root Cause Hypothesis:** {latest.hypothesis}

**Evidence:** {self._format_findings(context['findings'])}

Provide:
1. Clear root cause explanation
2. Step-by-step solution
3. How to verify the fix
4. Prevention measures

Output JSON:
{{
  "root_cause": "clear explanation",
  "solution": "step by step fix",
  "verification": "how to verify",
  "prevention": "how to prevent"
}}"""
                
                response = self.llm_agent._query_ollama(solution_prompt)
                
                import json
                import re
                json_match = re.search(r'\{.+\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group()
                    
                    # Sanitize JSON string - remove invalid control characters
                    # Replace control chars (except \n, \r, \t) with spaces
                    json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', json_str)
                    
                    try:
                        solution_data = json.loads(json_str)
                        return {
                            'root_cause': solution_data.get('root_cause', latest.hypothesis),
                            'confidence': latest.confidence,
                            'solution': solution_data.get('solution', 'See diagnostic output'),
                            'verification': solution_data.get('verification', ''),
                            'prevention': solution_data.get('prevention', '')
                        }
                    except json.JSONDecodeError as je:
                        print(f"   ⚠️  JSON parsing failed after sanitization: {je}")
                        # Continue to fallback
            except Exception as e:
                print(f"   ⚠️  Final LLM analysis failed: {e}")
        
        # Fallback: Use latest hypothesis
        return {
            'root_cause': latest.hypothesis,
            'confidence': latest.confidence,
            'solution': 'See investigation findings above for details'
        }
    
    def _format_investigation_history(self, history: List[InvestigationStep]) -> str:
        """Format history for LLM prompt"""
        if not history:
            return "No previous iterations"
        
        formatted = []
        for step in history:
            formatted.append(
                f"Iteration {step.iteration}: {step.hypothesis} "
                f"(confidence: {step.confidence:.2f})"
            )
        return "\n".join(formatted)
    
    def _extract_critical_sections(self, cmd: str, output: str) -> str:
        """
        Extract critical sections from kubectl output instead of truncating.
        Prioritizes Events, errors, and relevant diagnostic information.
        """
        if not output:
            return output
        
        # Handle 'kubectl describe pod' output
        if 'describe pod' in cmd or 'describe deployment' in cmd:
            return self._parse_describe_output(output)
        
        # Handle 'kubectl logs' output
        elif 'logs' in cmd or 'log' in cmd:
            return self._parse_logs_output(output)
        
        # For other commands, use smart truncation
        else:
            return output[:1000] if len(output) > 1000 else output
    
    def _generate_preview(self, cmd: str, output: str) -> str:
        """
        Generate an intelligent preview of command output for user display.
        Shows the most important information based on command type.
        """
        if not output:
            return "No output"
        
        # For describe commands, show critical errors from Events
        if 'describe pod' in cmd or 'describe deployment' in cmd:
            # Look for Events section
            if 'Events:' in output:
                events_section = output.split('Events:')[1] if 'Events:' in output else ''
                
                # Look for Warning/Failed events
                warning_lines = [line.strip() for line in events_section.split('\n') 
                                if 'Warning' in line or 'Failed' in line or 'Error:' in line]
                
                if warning_lines:
                    # Show first critical error
                    first_error = warning_lines[0][:150]
                    return f"⚠️  Critical Event: {first_error}"
            
            # No critical events, show basic info
            first_line = output.split('\n')[0] if output else ''
            return f"Found data: {first_line[:100]}..."
        
        # For logs, show if errors were found
        elif 'logs' in cmd or 'log' in cmd:
            error_keywords = ['error', 'fatal', 'panic', 'exception', 'failed']
            lines = output.split('\n')
            error_count = sum(1 for line in lines if any(kw in line.lower() for kw in error_keywords))
            
            if error_count > 0:
                return f"Found {error_count} error/warning line(s) in logs"
            else:
                return f"Found {len(lines)} log lines (no errors)"
        
        # For other commands, show simple preview
        else:
            preview = output[:150].replace('\n', ' ')
            return f"Found data: {preview}..."
    
    def _parse_describe_output(self, output: str) -> str:
        """
        Parse kubectl describe pod/deployment output.
        Extracts: Status, Conditions, Events (MOST IMPORTANT)
        """
        lines = output.split('\n')
        critical_sections = []
        
        # Extract basic info (first few lines)
        critical_sections.append("=== BASIC INFO ===")
        critical_sections.extend(lines[:5])  # Name, Namespace, Priority, etc.
        
        # Extract Status section
        in_status = False
        status_lines = []
        for i, line in enumerate(lines):
            if line.startswith('Status:'):
                in_status = True
                status_lines.append(line)
            elif in_status and line.startswith(' '):
                status_lines.append(line)
            elif in_status and not line.startswith(' '):
                break
        
        if status_lines:
            critical_sections.append("\n=== STATUS ===")
            critical_sections.extend(status_lines)
        
        # Extract Conditions section
        in_conditions = False
        conditions_lines = []
        for i, line in enumerate(lines):
            if line.startswith('Conditions:'):
                in_conditions = True
                conditions_lines.append(line)
                # Get next 10 lines or until next section
                for j in range(i+1, min(i+15, len(lines))):
                    if lines[j] and not lines[j][0].isspace() and ':' in lines[j]:
                        break
                    conditions_lines.append(lines[j])
                break
        
        if conditions_lines:
            critical_sections.append("\n=== CONDITIONS ===")
            critical_sections.extend(conditions_lines)
        
        # Extract State and Reason (for containers)
        state_lines = []
        for i, line in enumerate(lines):
            if 'State:' in line or 'Reason:' in line or 'Message:' in line:
                state_lines.append(line)
        
        if state_lines:
            critical_sections.append("\n=== CONTAINER STATE ===")
            critical_sections.extend(state_lines)
        
        # Extract Events section (MOST CRITICAL - contains actual errors)
        in_events = False
        events_lines = []
        for i, line in enumerate(lines):
            if line.startswith('Events:'):
                in_events = True
                events_lines.append(line)
                # Get all remaining lines (events are at the end)
                events_lines.extend(lines[i+1:])
                break
        
        if events_lines:
            critical_sections.append("\n=== EVENTS (CRITICAL) ===")
            critical_sections.extend(events_lines)
        
        return '\n'.join(critical_sections)
    
    def _parse_logs_output(self, output: str) -> str:
        """
        Parse kubectl logs output.
        Extracts: Error/Warning/Fatal lines + last 20 lines (most recent)
        """
        lines = output.split('\n')
        critical_lines = []
        
        # Extract error/warning/fatal/panic lines
        error_keywords = ['error', 'fatal', 'panic', 'exception', 'failed', 'warning', 'err:']
        error_lines = []
        
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in error_keywords):
                error_lines.append(line)
        
        if error_lines:
            critical_lines.append("=== ERRORS/WARNINGS IN LOGS ===")
            # Limit to first 15 error lines to avoid overwhelming
            critical_lines.extend(error_lines[:15])
            if len(error_lines) > 15:
                critical_lines.append(f"... and {len(error_lines) - 15} more error/warning lines")
        
        # Always include last 20 lines (most recent activity)
        critical_lines.append("\n=== LAST 20 LINES (MOST RECENT) ===")
        critical_lines.extend(lines[-20:] if len(lines) > 20 else lines)
        
        return '\n'.join(critical_lines)
    
    def _format_findings(self, findings: Dict) -> str:
        """Format findings for LLM prompt with intelligent parsing"""
        formatted = []
        for cmd, result in findings.items():
            if isinstance(result, dict):
                output = result.get('stdout', result.get('stderr', ''))
                
                # Use intelligent parsing instead of simple truncation
                parsed_output = self._extract_critical_sections(cmd, output)
                
                formatted.append(f"Command: {cmd}\nOutput:\n{parsed_output}\n")
        return "\n".join(formatted)
    
    def _check_llm_available(self) -> bool:
        """Check if LLM is available"""
        if not self.llm_agent:
            return False
        return self.llm_agent._check_ollama_available()
    
    def process(self, request: AgentRequest) -> AgentResponse:
        """Process investigation request"""
        start_time = time.time()
        
        try:
            result = self.investigate(
                initial_query=request.query,
                namespace=request.context.get('namespace', 'default'),
                pod_name=request.context.get('pod_name', '')
            )
            
            execution_time = time.time() - start_time
            
            return AgentResponse(
                success=True,
                data=result,
                error=None,
                metadata={
                    'iterations': result['iterations'],
                    'confidence': result['confidence']
                },
                agent_type=self.agent_type,
                execution_time=execution_time
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResponse(
                success=False,
                data={},
                error=str(e),
                metadata={},
                agent_type=self.agent_type,
                execution_time=execution_time
            )
    
    def health_check(self) -> bool:
        """Check if investigation agent is ready"""
        return self.llm_agent is not None
