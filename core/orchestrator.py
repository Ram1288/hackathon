"""DevDebug Orchestrator - Main coordination engine"""
from typing import Dict, List, Any, Optional
import uuid
import time
from datetime import datetime

from core.interfaces import AgentRequest, AgentResponse, BaseAgent
from agents.document_agent import DocumentAgent
from agents.execution_agent import ExecutionAgent
from agents.llm_agent import LLMAgent


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
        self.ai_driven_diagnostics = config.get('orchestrator', {}).get('ai_driven_diagnostics', True)
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
            
            # Step 2: Run diagnostics - AI-driven command generation
            print("\n🔍 Step 2: Running diagnostics...")
            
            if self.ai_driven_diagnostics:
                # Let LLM decide which commands to run
                print("🤖 Using AI to determine diagnostic commands...")
                diagnostic_commands = self.agents['llm'].generate_diagnostic_commands(
                    query=query,
                    namespace=namespace,
                    pod_name=pod_name or ""
                )
                
                if diagnostic_commands:
                    print(f"📋 Generated {len(diagnostic_commands)} diagnostic commands")
                    for cmd_obj in diagnostic_commands:
                        print(f"   • {cmd_obj.get('reason', 'Diagnostic')}: {cmd_obj.get('cmd', '')}")
                    
                    # Execute the AI-generated commands
                    exec_context = {
                        'ai_generated_commands': diagnostic_commands,
                        'namespace': namespace
                    }
                    if pod_name:
                        exec_context['pod_name'] = pod_name
                else:
                    # Fallback to template-based
                    print("⚠ Falling back to template-based diagnostics")
                    exec_context = {
                        'documentation': doc_response.data.get('documents', []) if doc_response.success else [],
                        'namespace': namespace
                    }
                    if pod_name:
                        exec_context['pod_name'] = pod_name
            else:
                # Use traditional template-based approach
                exec_context = {
                    'documentation': doc_response.data.get('documents', []) if doc_response.success else [],
                    'namespace': namespace
                }
                if pod_name:
                    exec_context['pod_name'] = pod_name
            
            exec_request = AgentRequest(
                query=query,
                context=exec_context,
                metadata={},
                session_id=session_id
            )
            exec_response = self.agents['execution'].process(exec_request)
            
            if exec_response.success:
                print(f"✓ Diagnostics completed (mode: {exec_response.metadata.get('mode', 'unknown')})")
            else:
                print(f"✗ Diagnostics failed: {exec_response.error}")
            
            # Step 3: Generate solution with LLM
            print("\n🤖 Step 3: Generating solution with LLM...")
            llm_context = {
                'diagnostics': exec_response.data if exec_response.success else {},
                'documentation': doc_response.data.get('documents', []) if doc_response.success else [],
                'code_examples': doc_response.data.get('code_examples', {}) if doc_response.success else {},
                'k8s_patterns': doc_response.data.get('k8s_patterns', []) if doc_response.success else []
            }
            
            llm_request = AgentRequest(
                query=query,
                context=llm_context,
                metadata={},
                session_id=session_id
            )
            llm_response = self.agents['llm'].process(llm_request)
            
            if llm_response.success:
                print(f"✓ Solution generated (model: {llm_response.metadata.get('model', 'unknown')})")
            else:
                print(f"⚠ LLM processing had issues: {llm_response.error}")
            
            # Combine results
            result = {
                'session_id': session_id,
                'query': query,
                'namespace': namespace,
                'solution': llm_response.data.get('response', 'Unable to generate solution') if llm_response.success else 'LLM unavailable',
                'diagnostics': exec_response.data if exec_response.success else {},
                'documentation': doc_response.data.get('documents', []) if doc_response.success else [],
                'code_examples': doc_response.data.get('code_examples', {}) if doc_response.success else {},
                'k8s_patterns': doc_response.data.get('k8s_patterns', []) if doc_response.success else [],
                'timestamp': time.time(),
                'metadata': {
                    'doc_agent': {
                        'success': doc_response.success,
                        'execution_time': doc_response.execution_time
                    },
                    'exec_agent': {
                        'success': exec_response.success,
                        'execution_time': exec_response.execution_time,
                        'mode': exec_response.metadata.get('mode') if exec_response.success else None
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
