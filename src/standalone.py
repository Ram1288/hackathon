"""Standalone CLI interface for DevDebug AI"""
import click
import yaml
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax

# Add parent directory to path to import core modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import DevDebugOrchestrator


console = Console()


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        console.print(f"[red]Error: Config file not found: {config_path}[/red]")
        console.print("[yellow]Creating default config...[/yellow]")
        return create_default_config(config_path)
    except Exception as e:
        console.print(f"[red]Error loading config: {e}[/red]")
        sys.exit(1)


def create_default_config(config_path: str) -> dict:
    """Create default configuration"""
    default_config = {
        'document_agent': {
            'doc_dir': './docs'
        },
        'execution_agent': {
            'ssh_enabled': False,
            'kubeconfig_path': '~/.kube/config'
        },
        'llm_agent': {
            'ollama_url': 'http://localhost:11434',
            'model': 'llama3.1:8b',
            'temperature': 0.7,
            'max_tokens': 1000
        },
        'orchestrator': {
            'max_session_history': 100,
            'session_timeout': 3600
        }
    }
    
    try:
        with open(config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
        console.print(f"[green]✓ Created default config at {config_path}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to create config: {e}[/red]")
    
    return default_config


@click.group()
def cli():
    """DevDebug AI - Intelligent Kubernetes Troubleshooting Assistant"""
    pass


@cli.command()
@click.option('--config', default='config.yaml', help='Config file path')
@click.option('--query', prompt='Describe your issue', help='Issue description')
@click.option('--namespace', default='default', help='Kubernetes namespace')
@click.option('--pod', default=None, help='Pod name (optional)')
@click.option('--session', default=None, help='Session ID (optional)')
def troubleshoot(config, query, namespace, pod, session):
    """Troubleshoot a Kubernetes issue"""
    
    console.print("\n[bold cyan]DevDebug AI - Kubernetes Troubleshooter[/bold cyan]\n")
    
    # Load config
    config_data = load_config(config)
    
    # Initialize orchestrator
    console.print("[yellow]Initializing agents...[/yellow]")
    try:
        orchestrator = DevDebugOrchestrator(config_data)
    except Exception as e:
        console.print(f"[red]Failed to initialize orchestrator: {e}[/red]")
        sys.exit(1)
    
    # Process query
    console.print(f"\n[bold]Analyzing: [/bold]{query}\n")
    
    result = orchestrator.process_query(
        query=query,
        session_id=session,
        namespace=namespace,
        pod_name=pod
    )
    
    # Display results
    if 'error' in result and not result.get('solution'):
        console.print(Panel(
            f"[red]Error: {result['error']}[/red]",
            title="❌ Error",
            border_style="red"
        ))
        return
    
    # Display solution
    console.print(Panel(
        Markdown(result['solution']),
        title="💡 Solution",
        border_style="green",
        expand=False
    ))
    
    # Display diagnostics if available
    if result.get('diagnostics'):
        console.print("\n[bold cyan]📊 Diagnostic Information:[/bold cyan]")
        diagnostics = result['diagnostics']
        
        if isinstance(diagnostics, dict):
            for key, value in list(diagnostics.items())[:3]:  # Show first 3
                if isinstance(value, dict) and 'stdout' in value:
                    output = value['stdout']
                    if output.strip():
                        console.print(f"\n[bold]{key}:[/bold]")
                        console.print(Syntax(output[:500], "bash", theme="monokai", line_numbers=False))
    
    # Display K8s patterns if matched
    if result.get('k8s_patterns'):
        console.print("\n[bold cyan]🔍 Matched K8s Patterns:[/bold cyan]")
        for pattern in result['k8s_patterns']:
            console.print(f"  • [yellow]{pattern['pattern']}[/yellow]")
    
    # Display session info
    console.print(f"\n[dim]Session ID: {result['session_id']}[/dim]")
    console.print(f"[dim]Namespace: {result.get('namespace', 'default')}[/dim]\n")


@cli.command()
@click.option('--config', default='config.yaml', help='Config file path')
def health(config):
    """Check health of all agents"""
    
    console.print("\n[bold cyan]DevDebug AI - Health Check[/bold cyan]\n")
    
    # Load config
    config_data = load_config(config)
    
    # Initialize orchestrator
    try:
        orchestrator = DevDebugOrchestrator(config_data)
    except Exception as e:
        console.print(f"[red]Failed to initialize orchestrator: {e}[/red]")
        sys.exit(1)
    
    # Get health status
    health_status = orchestrator.health_check()
    
    # Display results
    console.print(f"[bold]Overall Status:[/bold] {'✓ Healthy' if health_status['overall_healthy'] else '✗ Unhealthy'}\n")
    
    console.print("[bold]Agent Status:[/bold]")
    for agent_name, status in health_status['agents'].items():
        is_healthy = status.get('healthy', False)
        symbol = "✓" if is_healthy else "✗"
        color = "green" if is_healthy else "red"
        
        console.print(f"  {symbol} [{color}]{agent_name}[/{color}]: {status.get('type', 'unknown')}")
        if 'error' in status:
            console.print(f"    [red]Error: {status['error']}[/red]")
    
    console.print()


@cli.command()
@click.option('--config', default='config.yaml', help='Config file path')
def interactive(config):
    """Start interactive troubleshooting session"""
    
    console.print("\n[bold cyan]DevDebug AI - Interactive Mode[/bold cyan]")
    console.print("[dim]Type 'exit' or 'quit' to end session[/dim]\n")
    
    # Load config
    config_data = load_config(config)
    
    # Initialize orchestrator
    console.print("[yellow]Initializing agents...[/yellow]")
    try:
        orchestrator = DevDebugOrchestrator(config_data)
    except Exception as e:
        console.print(f"[red]Failed to initialize orchestrator: {e}[/red]")
        sys.exit(1)
    
    console.print("[green]✓ Ready for troubleshooting![/green]\n")
    
    session_id = None
    namespace = "default"
    
    while True:
        try:
            # Get user input
            query = console.input("[bold cyan]You:[/bold cyan] ")
            
            if query.lower() in ['exit', 'quit', 'q']:
                console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
                break
            
            if not query.strip():
                continue
            
            # Handle special commands
            if query.startswith('/'):
                if query.startswith('/namespace '):
                    namespace = query.split()[1]
                    console.print(f"[green]✓ Namespace set to: {namespace}[/green]\n")
                    continue
                elif query == '/clear':
                    if session_id:
                        orchestrator.clear_session(session_id)
                        session_id = None
                        console.print("[green]✓ Session cleared[/green]\n")
                    continue
                elif query == '/health':
                    health_status = orchestrator.health_check()
                    overall = "✓ Healthy" if health_status['overall_healthy'] else "✗ Unhealthy"
                    console.print(f"[bold]Status:[/bold] {overall}\n")
                    continue
            
            # Process query
            result = orchestrator.process_query(
                query=query,
                session_id=session_id,
                namespace=namespace
            )
            
            session_id = result['session_id']
            
            # Display solution
            console.print("\n[bold cyan]DevDebug:[/bold cyan]")
            console.print(Markdown(result['solution']))
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted. Type 'exit' to quit.[/yellow]\n")
            continue
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]\n")


@cli.command()
def setup():
    """Setup wizard for first-time configuration"""
    
    console.print("\n[bold cyan]DevDebug AI - Setup Wizard[/bold cyan]\n")
    
    # Check if Ollama is installed
    console.print("[bold]Checking requirements...[/bold]")
    
    import subprocess
    
    # Check kubectl
    try:
        subprocess.run(['kubectl', 'version', '--client'], capture_output=True, timeout=5)
        console.print("  ✓ [green]kubectl found[/green]")
    except:
        console.print("  ✗ [yellow]kubectl not found (optional)[/yellow]")
    
    # Check Ollama
    try:
        import requests
        response = requests.get('http://localhost:11434/api/tags', timeout=2)
        if response.status_code == 200:
            console.print("  ✓ [green]Ollama is running[/green]")
        else:
            console.print("  ✗ [yellow]Ollama not responding[/yellow]")
    except:
        console.print("  ✗ [red]Ollama not running[/red]")
        console.print("    [dim]Install: curl -fsSL https://ollama.ai/install.sh | sh[/dim]")
        console.print("    [dim]Start: ollama serve[/dim]")
        console.print("    [dim]Pull model: ollama pull llama3.1:8b[/dim]")
    
    # Create config
    console.print("\n[bold]Creating configuration...[/bold]")
    create_default_config('config.yaml')
    
    # Create docs directory
    from pathlib import Path
    docs_dir = Path('./docs')
    if not docs_dir.exists():
        docs_dir.mkdir(parents=True)
        console.print(f"  ✓ [green]Created docs directory[/green]")
    
    console.print("\n[green]✓ Setup complete![/green]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("  1. Add documentation to ./docs/")
    console.print("  2. Run: devdebug troubleshoot --query 'your issue'")
    console.print("  3. Or: devdebug interactive\n")


if __name__ == '__main__':
    cli()
