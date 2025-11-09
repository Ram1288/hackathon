# Kubernetes Troubleshooting Guide

## Common Pod Issues

### CrashLoopBackOff

**Description:** Pod is repeatedly crashing and Kubernetes is backing off restart attempts.

**Common Causes:**
- Application error on startup
- Missing dependencies or configuration
- Insufficient resources (CPU/Memory)
- Failed health checks

**Diagnosis Commands:**

```bash
# Check pod status
kubectl get pods -n <namespace>

# View pod logs (current)
kubectl logs <pod-name> -n <namespace>

# View pod logs (previous crash)
kubectl logs <pod-name> -n <namespace> --previous

# Describe pod for events
kubectl describe pod <pod-name> -n <namespace>

# Check recent events
kubectl get events -n <namespace> --sort-by=.lastTimestamp
```

**Python Example:**

```python
from kubernetes import client, config

# Load kubeconfig
config.load_kube_config()
v1 = client.CoreV1Api()

# Get pod logs
pod_logs = v1.read_namespaced_pod_log(
    name='pod-name',
    namespace='namespace',
    tail_lines=100
)
print("Pod Logs:", pod_logs)

# Get pod status
pod = v1.read_namespaced_pod(name='pod-name', namespace='namespace')
print("Pod Phase:", pod.status.phase)
print("Container Status:")
for status in pod.status.container_statuses:
    print(f"  {status.name}: {status.state}")
```

**Solutions:**
1. Check application logs for startup errors
2. Verify environment variables and config maps
3. Check resource limits and requests
4. Verify liveness and readiness probes

---

### ImagePullBackOff

**Description:** Kubernetes cannot pull the container image from the registry.

**Common Causes:**
- Incorrect image name or tag
- Private registry without authentication
- Network connectivity issues
- Registry is down or unreachable

**Diagnosis Commands:**

```bash
# Describe pod to see image pull details
kubectl describe pod <pod-name> -n <namespace>

# Check if image pull secret exists
kubectl get secrets -n <namespace>

# Verify image exists in registry
docker pull <image-name>:<tag>
```

**Python Example:**

```python
from kubernetes import client, config

config.load_kube_config()
v1 = client.CoreV1Api()

# Check pod for image pull errors
pod = v1.read_namespaced_pod(name='pod-name', namespace='namespace')

for status in pod.status.container_statuses or []:
    if status.state.waiting and 'ImagePull' in status.state.waiting.reason:
        print(f"Container: {status.name}")
        print(f"Image: {status.image}")
        print(f"Reason: {status.state.waiting.reason}")
        print(f"Message: {status.state.waiting.message}")
```

**Solutions:**
1. Verify image name and tag are correct
2. Create imagePullSecret for private registries:
   ```bash
   kubectl create secret docker-registry regcred \
     --docker-server=<registry> \
     --docker-username=<username> \
     --docker-password=<password> \
     --docker-email=<email> \
     -n <namespace>
   ```
3. Add imagePullSecrets to pod spec
4. Check network connectivity to registry

---

### OOMKilled (Out of Memory)

**Description:** Container was killed because it exceeded memory limits.

**Common Causes:**
- Memory limit set too low
- Memory leak in application
- Unexpected load or data volume
- No memory limits set (unbounded growth)

**Diagnosis Commands:**

```bash
# Check pod resource usage
kubectl top pod <pod-name> -n <namespace>

# View resource limits
kubectl get pod <pod-name> -n <namespace> -o yaml | grep -A 10 resources

# Check events for OOM
kubectl get events -n <namespace> --field-selector reason=OOMKilling
```

**Python Example:**

```python
from kubernetes import client, config

config.load_kube_config()
v1 = client.CoreV1Api()

# Get pod resource configuration
pod = v1.read_namespaced_pod(name='pod-name', namespace='namespace')

for container in pod.spec.containers:
    print(f"Container: {container.name}")
    
    if container.resources.limits:
        print(f"  Memory Limit: {container.resources.limits.get('memory', 'Not set')}")
        print(f"  CPU Limit: {container.resources.limits.get('cpu', 'Not set')}")
    
    if container.resources.requests:
        print(f"  Memory Request: {container.resources.requests.get('memory', 'Not set')}")
        print(f"  CPU Request: {container.resources.requests.get('cpu', 'Not set')}")
```

**Solutions:**
1. Increase memory limits:
   ```yaml
   resources:
     limits:
       memory: "2Gi"
     requests:
       memory: "1Gi"
   ```
2. Investigate memory leaks in application
3. Implement proper memory profiling
4. Use Horizontal Pod Autoscaler (HPA) for load distribution

---

### Pending Pods

**Description:** Pod remains in Pending state and is not scheduled to any node.

**Common Causes:**
- Insufficient resources on nodes
- Node selector/affinity not matching
- Taints preventing scheduling
- PersistentVolume not available

**Diagnosis Commands:**

```bash
# Check pod status
kubectl describe pod <pod-name> -n <namespace>

# Check node resources
kubectl top nodes
kubectl get nodes -o wide

# Check node capacity
kubectl describe nodes
```

**Python Example:**

```python
from kubernetes import client, config

config.load_kube_config()
v1 = client.CoreV1Api()

# Check pod conditions
pod = v1.read_namespaced_pod(name='pod-name', namespace='namespace')

print(f"Pod Phase: {pod.status.phase}")
print("\nPod Conditions:")
for condition in pod.status.conditions or []:
    print(f"  {condition.type}: {condition.status}")
    if condition.message:
        print(f"    Message: {condition.message}")

# Check node availability
print("\nNode Resources:")
nodes = v1.list_node()
for node in nodes.items:
    print(f"  {node.metadata.name}: {node.status.allocatable}")
```

**Solutions:**
1. Add more nodes or increase node resources
2. Adjust resource requests to fit available nodes
3. Remove or adjust node selectors/affinity rules
4. Check and resolve node taints
5. Ensure required PersistentVolumes are available

---

## Monitoring and Debugging

### Get All Resource Usage

```bash
# Pod resource usage
kubectl top pods -n <namespace>

# Node resource usage
kubectl top nodes

# All resources in namespace
kubectl get all -n <namespace>
```

### Check Cluster Events

```bash
# All recent events
kubectl get events -n <namespace> --sort-by=.lastTimestamp

# Warning events only
kubectl get events -n <namespace> --field-selector type=Warning

# Events for specific pod
kubectl get events -n <namespace> --field-selector involvedObject.name=<pod-name>
```

### Python Script to Monitor All Pods

```python
from kubernetes import client, config
import time

config.load_kube_config()
v1 = client.CoreV1Api()

def monitor_pods(namespace='default'):
    """Monitor all pods in a namespace"""
    while True:
        pods = v1.list_namespaced_pod(namespace)
        
        print(f"\n{'='*80}")
        print(f"Pod Status Summary - Namespace: {namespace}")
        print(f"{'='*80}")
        
        status_counts = {}
        problematic_pods = []
        
        for pod in pods.items:
            phase = pod.status.phase
            status_counts[phase] = status_counts.get(phase, 0) + 1
            
            # Check for problematic pods
            if phase not in ['Running', 'Succeeded']:
                problematic_pods.append({
                    'name': pod.metadata.name,
                    'phase': phase,
                    'reason': pod.status.reason if pod.status.reason else 'Unknown'
                })
        
        # Print summary
        print(f"\nStatus Counts:")
        for phase, count in status_counts.items():
            print(f"  {phase}: {count}")
        
        # Print problematic pods
        if problematic_pods:
            print(f"\n⚠ Problematic Pods:")
            for pod in problematic_pods:
                print(f"  - {pod['name']}: {pod['phase']} ({pod['reason']})")
        else:
            print(f"\n✓ All pods healthy!")
        
        time.sleep(30)  # Check every 30 seconds

if __name__ == '__main__':
    monitor_pods('default')
```

## Best Practices

### Resource Limits

Always set resource requests and limits:

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Health Checks

Implement liveness and readiness probes:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
```

### Logging

Structure your application logs for easy debugging:
- Use structured logging (JSON)
- Include correlation IDs
- Log appropriate level (ERROR, WARN, INFO, DEBUG)
- Avoid logging sensitive data
