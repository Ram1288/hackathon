"""Orchestrator for coordinating AI agents"""
import time
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.interfaces import AgentRequest, BaseAgent
from agents.document_agent import DocumentAgent
from agents.execution_agent import ExecutionAgent
from agents.llm_agent import LLMAgent
from agents.investigator_agent import InvestigatorAgent
from agents.investigation_agent import InvestigationAgent


class DevDebugOrchestrator:
    """
    Main orchestrator that coordinates all agents
    Implements the RAG + Execution + LLM pipeline
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize orchestrator with configuration
        
        Args:
            config: Configuration dictionary containing settings for all agents
        """
        self.config = config
        self.agents = {}
        self.session_store = {}
        self.max_session_history = config.get('orchestrator', {}).get('max_session_history', 100)
        self.session_timeout = config.get('orchestrator', {}).get('session_timeout', 3600)
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize all agents"""
        try:
            # Document Agent
            print("Initializing Document Agent...")
            self.agents['document'] = DocumentAgent(
                self.config.get('document_agent', {})
            )
            
            # Execution Agent
            print("Initializing Execution Agent...")
            self.agents['execution'] = ExecutionAgent(
                self.config.get('execution_agent', {})
            )
            
            # LLM Agent
            print("Initializing LLM Agent...")
            self.agents['llm'] = LLMAgent(
                self.config.get('llm_agent', {})
            )
            
            # Investigator Agent (Pattern recognition and iterative analysis)
            print("Initializing Investigator Agent...")
            self.agents['investigator'] = InvestigatorAgent(
                self.config.get('investigator_agent', {})
            )
            
            # Investigation Agent (AI-driven iterative troubleshooting)
            print("Initializing Investigation Agent...")
            self.agents['investigation'] = InvestigationAgent(
                self.config.get('investigation_agent', {})
            )
            # Inject dependencies
            self.agents['investigation'].set_agents(
                self.agents['llm'],
                self.agents['execution']
            )
            
            print("✓ All agents initialized successfully")
        except Exception as e:
            print(f"✗ Agent initialization failed: {e}")
            raise
    
    def process_query(
        self, 
        query: str, 
        session_id: Optional[str] = None,
        namespace: str = "default",
        pod_name: Optional[str] = None
    ) -> Dict:
        """
        Main entry point for processing queries
        Orchestrates the RAG + Execution + LLM pipeline
        
        Args:
            query: User's troubleshooting query
            session_id: Optional session ID for maintaining context
            namespace: Kubernetes namespace (default: "default")
            pod_name: Optional pod name for specific pod queries
            
        Returns:
            Dictionary containing solution, diagnostics, and documentation
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Initialize session context
        if session_id not in self.session_store:
            self.session_store[session_id] = {
                'history': [],
                'context': {},
                'created_at': datetime.now(),
                'last_access': datetime.now()
            }
        
        # Update last access
        self.session_store[session_id]['last_access'] = datetime.now()
        
        print(f"\n{'='*60}")
        print(f"Processing Query (Session: {session_id[:8]}...)")
        print(f"Query: {query}")
        print(f"{'='*60}\n")
        
        try:
            # Determine query intent (action, informational, or troubleshooting)
            query_intent = self._determine_query_intent(query)
            
            print(f"🎯 Query Intent: {query_intent.upper()}\n")
            
            if query_intent == 'action':
                # User wants to execute a command (delete, create, etc.)
                return self._process_action_query(query, namespace, pod_name, session_id)
            elif query_intent == 'informational':
                # User wants simple information (who, what, which, show, list)
                return self._process_informational_query(query, namespace, pod_name, session_id)
            else:
                # User wants troubleshooting/debugging (why, fix, debug)
                return self._process_troubleshooting_query(query, namespace, pod_name, session_id)
                
        except Exception as e:
            print(f"\n✗ Error processing query: {e}\n")
            return {
                'session_id': session_id,
                'query': query,
                'namespace': namespace,
                'error': str(e),
                'timestamp': time.time(),
                'solution': f"An error occurred: {str(e)}"
            }
    
    def _determine_query_intent(self, query: str) -> str:
        """
        Determine query intent with 3-tier classification.
        
        Priority Order (highest to lowest):
        1. ACTION - User wants to execute a command (delete, create, scale, etc.)
        2. TROUBLESHOOTING - User wants to debug/fix a problem (debug, fix, why, error)
        3. INFORMATIONAL - User wants simple info (who, what, which, show, list)
        
        Returns:
            'action' - User wants to execute a command
            'troubleshooting' - User wants to debug/fix a problem
            'informational' - User wants simple info (default)
        """
        import re
        
        query_lower = query.lower()
        
        # Action keywords - user wants to DO something (HIGHEST PRIORITY)
        action_keywords = [
            'delete', 'remove', 'create', 'add', 'apply', 
            'scale', 'restart', 'rollout', 'patch', 'edit',
            'drain', 'cordon', 'uncordon', 'taint', 'label',
            'exec', 'run', 'expose', 'port-forward'
        ]
        
        # Troubleshooting keywords - problem investigation (MEDIUM PRIORITY)
        troubleshooting_keywords = [
            'debug', 'troubleshoot', 'diagnose', 'investigate', 
            'why', 'how', 'fix', 'resolve', 'solve',
            'failing', 'failed', 'error', 'issue', 'problem',
            'not working', 'broken', 'crash'
        ]
        
        # Informational keywords - simple queries (LOWEST PRIORITY)
        informational_keywords = [
            'who', 'which', 'what', 'show', 'list', 'get', 'describe',
            'check', 'display', 'print', 'view'
        ]
        
        # Helper function to check for word boundaries
        def has_keyword(keywords, text):
            for keyword in keywords:
                # Use word boundaries to avoid false positives like "run" in "running"
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, text):
                    return True
            return False
        
        # Check ACTION keywords FIRST (highest priority)
        # "delete which pods" → action (delete wins over which)
        if has_keyword(action_keywords, query_lower):
            return 'action'
        
        # Check troubleshooting keywords SECOND
        # "debug pods" → troubleshooting
        # "list failing pods" → troubleshooting (failing wins over list)
        if has_keyword(troubleshooting_keywords, query_lower):
            return 'troubleshooting'
        
        # Check informational keywords LAST
        # "list pods" → informational (no action/troubleshooting words)
        if has_keyword(informational_keywords, query_lower):
            return 'informational'
        
        # Default to informational (safer than troubleshooting)
        return 'informational'
    
    def _process_action_query(self, query: str, namespace: str, pod_name: str, session_id: str) -> Dict:
        """
        Process an action request - generate and execute commands.
        
        Args:
            query: User's command request (e.g., "delete pods not running")
            namespace: K8s namespace
            pod_name: Optional pod name
            session_id: Session ID
            
        Returns:
            Dictionary with execution results
        """
        print("🎯 Action Request Detected - Generating commands...\n")
        
        # Step 1: Generate commands using LLM with ACTION-specific prompt
        print("📋 Step 1: Generating kubectl action commands...")
        commands = self.agents['llm'].generate_action_commands(
            query=query,
            namespace=namespace,
            pod_name=pod_name
        )
        
        if not commands:
            return {
                'session_id': session_id,
                'query': query,
                'namespace': namespace,
                'error': 'Could not generate commands for this action',
                'timestamp': time.time(),
                'solution': 'Unable to generate appropriate kubectl commands. Please rephrase your request.'
            }
        
        print(f"✓ Generated {len(commands)} command(s)\n")
        
        # Step 2: Show commands to user and ask for confirmation
        print("📝 Commands to execute:")
        for i, cmd_obj in enumerate(commands, 1):
            print(f"   {i}. {cmd_obj['cmd']}")
            print(f"      Reason: {cmd_obj['reason']}\n")
        
        # Step 3: Execute commands
        print("⚡ Step 2: Executing commands...\n")
        execution_results = {}
        
        for cmd_obj in commands:
            cmd = cmd_obj['cmd']
            print(f"   ▶ {cmd}")
            
            # Execute via execution agent
            exec_request = AgentRequest(
                query=query,
                context={
                    'ai_generated_commands': [cmd_obj],
                    'namespace': namespace
                },
                metadata={},
                session_id=session_id
            )
            
            exec_response = self.agents['execution'].process(exec_request)
            
            if exec_response.success:
                result = exec_response.data.get('results', {}).get(cmd, {})
                if result.get('stdout'):
                    print(f"      ✓ {result['stdout'][:100]}")
                else:
                    print(f"      ✓ Command executed successfully")
                execution_results[cmd] = result
            else:
                print(f"      ✗ Failed: {exec_response.error}")
                execution_results[cmd] = {'error': exec_response.error}
        
        # Step 3: Generate summary
        print("\n🤖 Step 3: Generating summary...\n")
        
        summary = self._generate_action_summary(query, commands, execution_results)
        
        print(f"{'='*60}")
        print("✓ Action completed")
        print(f"{'='*60}\n")
        
        return {
            'session_id': session_id,
            'query': query,
            'namespace': namespace,
            'query_type': 'action',
            'commands_executed': [cmd['cmd'] for cmd in commands],
            'execution_results': execution_results,
            'solution': summary,
            'timestamp': time.time(),
            'metadata': {
                'commands_count': len(commands),
                'success': all('error' not in r for r in execution_results.values())
            }
        }
    
    def _process_informational_query(self, query: str, namespace: str, pod_name: str, session_id: str) -> Dict:
        """
        Process a simple informational query - fast path without full investigation.
        For queries like "list pods", "show deployments", "who scheduled", etc.
        """
        print("ℹ️  Informational Query - Fast path\n")
        
        # Step 1: Generate simple diagnostic commands
        print("📋 Step 1: Generating kubectl commands...")
        commands = self.agents['llm'].generate_diagnostic_commands(
            query=query,
            namespace=namespace,
            pod_name=pod_name or ""
        )
        
        if not commands:
            return {
                'session_id': session_id,
                'query': query,
                'namespace': namespace,
                'error': 'Could not generate commands',
                'timestamp': time.time(),
                'solution': 'Unable to generate appropriate kubectl commands.'
            }
        
        print(f"✓ Generated {len(commands)} command(s)\n")
        
        # Step 2: Execute commands
        print("⚡ Step 2: Executing commands...\n")
        execution_results = {}
        
        for cmd_obj in commands:
            cmd = cmd_obj['cmd']
            print(f"   ▶ {cmd}")
            
            # IMPORTANT: Pass commands in context as 'ai_generated_commands'
            # The execution agent expects this format
            exec_request = AgentRequest(
                query=query,  # Original user query
                context={
                    'namespace': namespace,
                    'ai_generated_commands': [cmd_obj]  # Pass as AI-generated command
                },
                metadata={'command_type': 'kubectl'},
                session_id=session_id
            )
            exec_response = self.agents['execution'].process(exec_request)
            
            if exec_response.success:
                # Execution agent returns: {cmd: {stdout, stderr, returncode}}
                cmd_result = exec_response.data.get(cmd, exec_response.data)
                output = cmd_result.get('stdout', '')
                if output:
                    print(f"      ✓ {output[:100]}...")
                else:
                    print(f"      ✓ Command executed")
                execution_results[cmd] = cmd_result
            else:
                print(f"      ✗ {exec_response.error}")
                execution_results[cmd] = {'error': exec_response.error}
        
        # Step 3: Use LLM to answer the question directly from the results
        print("\n🤖 Step 3: Generating answer...\n")
        
        llm_context = {
            'diagnostics': execution_results,
            'root_cause': 'Informational query - no troubleshooting needed',
            'documentation': [],
            'code_examples': {}
        }
        
        llm_request = AgentRequest(
            query=f"{query}\n\nPlease provide a direct, concise answer based on the kubectl output above.",
            context=llm_context,
            metadata={},
            session_id=session_id
        )
        llm_response = self.agents['llm'].process(llm_request)
        
        if llm_response.success:
            solution_text = llm_response.data.get('response', 'No answer generated')
        else:
            # Fallback: show the raw data
            solution_text = f"**Query:** {query}\n\n**Results:**\n"
            for cmd, result in execution_results.items():
                if 'stdout' in result:
                    solution_text += f"\n```\n{result['stdout'][:500]}\n```\n"
        
        result = {
            'session_id': session_id,
            'query': query,
            'namespace': namespace,
            'query_type': 'informational',
            'solution': solution_text,
            'diagnostics': execution_results,
            'commands_executed': [cmd['cmd'] for cmd in commands],
            'timestamp': time.time(),
            'metadata': {
                'fast_path': True,
                'commands_count': len(commands)
            }
        }
        
        self._store_in_session(session_id, result)
        
        print(f"{'='*60}")
        print("✓ Query answered")
        print(f"{'='*60}\n")
        
        return result
    
    def _process_troubleshooting_query(self, query: str, namespace: str, pod_name: str, session_id: str) -> Dict:
        """
        Process a troubleshooting/diagnostic request.
        Performs full investigation including RAG, iterative diagnosis, and root cause analysis.
        """
        # Step 1: Search documentation (RAG)
        print("📚 Step 1: Searching documentation...")
        doc_request = AgentRequest(
            query=query,
            context={'namespace': namespace},
            metadata={},
            session_id=session_id
        )
        doc_response = self.agents['document'].process(doc_request)
        
        if doc_response.success:
            print(f"✓ Found {doc_response.metadata.get('doc_count', 0)} relevant documents")
            print(f"✓ Matched {doc_response.metadata.get('patterns_found', 0)} K8s patterns")
        else:
            print(f"✗ Documentation search failed: {doc_response.error}")
        
        # Step 2: Use ITERATIVE INVESTIGATION instead of one-shot diagnostics
        print("\n🔍 Step 2: Starting AI-driven iterative investigation...")
        
        investigation_result = self.agents['investigation'].investigate(
            initial_query=query,
            namespace=namespace,
            pod_name=pod_name or ""
        )
        
        print(f"✓ Investigation completed in {investigation_result['iterations']} iteration(s)")
        print(f"✓ Confidence: {investigation_result['confidence']*100:.1f}%")
        
        # Step 3: Generate comprehensive solution with LLM (if available and needed)
        print("\n🤖 Step 3: Generating comprehensive solution...")
        
        llm_context = {
            'diagnostics': investigation_result['all_findings'],
            'root_cause': investigation_result['final_hypothesis'],
            'investigation_path': investigation_result['investigation_path'],
            'documentation': doc_response.data.get('documents', []) if doc_response.success else [],
            'code_examples': doc_response.data.get('code_examples', {}) if doc_response.success else []
        }
        
        llm_request = AgentRequest(
            query=f"{query}\n\nInvestigation found: {investigation_result['final_hypothesis']}",
            context=llm_context,
            metadata={},
            session_id=session_id
        )
        llm_response = self.agents['llm'].process(llm_request)
        
        if llm_response.success:
            print(f"✓ Solution generated (model: {llm_response.metadata.get('model', 'unknown')})")
            solution_text = llm_response.data.get('response', investigation_result['solution'])
        else:
            print(f"⚠ LLM unavailable, using investigation findings")
            solution_text = f"**Root Cause:** {investigation_result['final_hypothesis']}\n\n{investigation_result['solution']}"
        
        # Combine results
        result = {
            'session_id': session_id,
            'query': query,
            'namespace': namespace,
            'query_type': 'troubleshooting',
            'solution': solution_text,
            'investigation_findings': investigation_result.get('all_findings', {}),
            'diagnostics': investigation_result.get('all_diagnostics', {}),
            'documentation': doc_response.data.get('documents', []) if doc_response.success else [],
            'code_examples': doc_response.data.get('code_examples', {}) if doc_response.success else {},
            'k8s_patterns': doc_response.data.get('k8s_patterns', []) if doc_response.success else [],
            'timestamp': time.time(),
            'metadata': {
                'doc_agent': {
                    'success': doc_response.success,
                    'execution_time': doc_response.execution_time
                },
                'investigation': {
                    'iterations': investigation_result.get('iterations', 0),
                    'confidence': investigation_result.get('confidence', 0.0),
                    'investigation_path': investigation_result.get('investigation_path', [])
                },
                'llm_agent': {
                    'success': llm_response.success,
                    'execution_time': llm_response.execution_time,
                    'model': llm_response.metadata.get('model') if llm_response.success else None
                }
            }
        }
        
        # Store in session
        self._store_in_session(session_id, result)
        
        print(f"\n{'='*60}")
        print("✓ Query processing completed successfully")
        print(f"{'='*60}\n")
        
        return result
    
    def _generate_action_summary(self, query: str, commands: List[Dict], results: Dict) -> str:
        """Generate a summary of action execution"""
        success_count = sum(1 for r in results.values() if 'error' not in r)
        total_count = len(results)
        
        summary = f"# Action Execution Summary\n\n"
        summary += f"**Query:** {query}\n\n"
        summary += f"**Commands Executed:** {total_count}\n"
        summary += f"**Successful:** {success_count}/{total_count}\n\n"
        
        summary += "## Execution Details:\n\n"
        for cmd_obj in commands:
            cmd = cmd_obj['cmd']
            result = results.get(cmd, {})
            
            if 'error' in result:
                summary += f"❌ **{cmd}**\n"
                summary += f"   Error: {result['error']}\n\n"
            else:
                summary += f"✅ **{cmd}**\n"
                if result.get('stdout'):
                    summary += f"   Output: {result['stdout'][:200]}\n\n"
                else:
                    summary += f"   Executed successfully\n\n"
        
        if success_count == total_count:
            summary += "\n✅ All commands executed successfully!"
        elif success_count > 0:
            summary += f"\n⚠️ {total_count - success_count} command(s) failed. Check details above."
        else:
            summary += "\n❌ All commands failed. Check permissions and cluster connectivity."
        
        return summary
    
    def _store_in_session(self, session_id: str, result: Dict):
        """Store result in session history"""
        if session_id in self.session_store:
            history = self.session_store[session_id]['history']
            history.append(result)
            
            # Trim history if too long
            if len(history) > self.max_session_history:
                history.pop(0)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health of all agents
        
        Returns:
            Dictionary with health status of each agent
        """
        health_status = {
            'orchestrator': True,
            'timestamp': datetime.now().isoformat(),
            'agents': {}
        }
        
        for name, agent in self.agents.items():
            try:
                is_healthy = agent.health_check()
                health_status['agents'][name] = {
                    'healthy': is_healthy,
                    'type': agent.agent_type.value if agent.agent_type else 'unknown'
                }
            except Exception as e:
                health_status['agents'][name] = {
                    'healthy': False,
                    'error': str(e)
                }
        
        # Overall health
        health_status['overall_healthy'] = all(
            status.get('healthy', False) 
            for status in health_status['agents'].values()
        )
        
        return health_status
    
    def get_session_history(self, session_id: str) -> List[Dict]:
        """
        Get session history
        
        Args:
            session_id: Session ID to retrieve
            
        Returns:
            List of previous interactions in this session
        """
        if session_id in self.session_store:
            return self.session_store[session_id]['history']
        return []
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear a specific session
        
        Args:
            session_id: Session ID to clear
            
        Returns:
            True if session was cleared, False if not found
        """
        if session_id in self.session_store:
            del self.session_store[session_id]
            return True
        return False
    
    def cleanup_old_sessions(self):
        """Cleanup sessions older than session_timeout"""
        current_time = datetime.now()
        sessions_to_remove = []
        
        for session_id, session_data in self.session_store.items():
            last_access = session_data.get('last_access', session_data.get('created_at'))
            age = (current_time - last_access).total_seconds()
            
            if age > self.session_timeout:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            del self.session_store[session_id]
        
        return len(sessions_to_remove)
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about all agents"""
        info = {}
        for name, agent in self.agents.items():
            info[name] = {
                'type': agent.agent_type.value if agent.agent_type else 'unknown',
                'initialized': agent.initialized,
                'config_keys': list(agent.config.keys())
            }
        return info
    
    def shutdown(self):
        """Shutdown all agents gracefully"""
        print("\nShutting down DevDebug Orchestrator...")
        for name, agent in self.agents.items():
            try:
                agent.cleanup()
                print(f"✓ {name} agent cleaned up")
            except Exception as e:
                print(f"✗ Error cleaning up {name} agent: {e}")
        print("✓ Shutdown complete")
