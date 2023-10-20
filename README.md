# azure-devops-aks-cluster


# Agent pool

```yaml
pool:
  name: MiAgentPool

```

# Scale Down

./run.sh --once

```yaml
spec:
  replicas: 0
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: azure-devops-agent
        image: [YOUR_AGENT_IMAGE]
        # ... otras configuraciones del contenedor ...
``````