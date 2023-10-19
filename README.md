# azure-devops-aks-cluster




# Scale Down

./run.sh --once

```bash
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