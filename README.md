# Azure DevOps K8s Cluster Autoscaler

This project provides a solution for automatically scaling Azure DevOps agents within a Kubernetes (AKS & EKS) cluster based on the queue of pending jobs in Azure DevOps. This project is using a "polling" aproach to check the queue of pending jobs in Azure DevOps and scale the agents accordingly and avoid the need of a webhook and a public endpoint.

## Project Structure

```graphql
azure-devops-aks-cluster
├── k8s-devops
│   ├── Dockerfile                # Dockerfile for the polling container.
│   ├── job-agent-ado             # Definition and tools for the Azure DevOps agent job.
│   │   ├── Dockerfile            # Dockerfile for the Azure DevOps agent job.
│   │   ├── job.yaml              # Job definition for Kubernetes.
│   │   └── start.sh              # Startup script to set up and launch the Azure DevOps agent in ephemeral mode.
│   ├── pod.yaml                  # Pod definition for the polling container.
│   ├── polling.py                # Main script that monitors Azure DevOps and triggers jobs in Kubernetes based on demand.
│   ├── rbac.yaml                 # Definition of roles and permissions for the polling container.
│   ├── requirements.txt          # Python dependencies required for the polling container.
│   ├── secrets.yaml              # Secrets definition for Kubernetes.
│   └── test_api.py               # API testing script, used for debugging and reverse engineering of the Azure DevOps API.
```

## Core Components

1. __polling.py:__ This is the heart of the solution. This script continuously monitors Azure DevOps for pending jobs. If it detects queued jobs, it triggers the creation of new agents in the AKS cluster.
2. __job-agent-ado:__ This folder contains the necessary tools and configurations to launch an Azure DevOps agent in a Kubernetes pod. The agent is started in ephemeral mode, meaning it will perform a job and then terminate.
3. __Dockerfiles:__ The Dockerfiles for the polling container and the Azure DevOps agent job.
4. __rbac.yaml and secrets.yaml:__ These files contain the Kubernetes definitions for the roles and permissions required by the polling container to let _polling.py_ to control K8s and the secrets required to connect to Azure DevOps.

## How to use it

1. __Prepare your agent:__ The file `k8s-devops/job-agent-ado/Dockerfile` needs to be adapted to your needs. You need to install the tools and dependencies required by your build and deployment pipeline. You can also add your own tools and scripts. The agent is started in ephemeral mode, meaning it will perform a job and then terminate.

2. __Adapt pod.yaml and job.yaml:__ Both files refers to a Docker image in DockerHub with a default configuration. You need to adapt both yamls according with the image name you will use.

3. __Build both Docker images:__ You need to build both Docker images and push them to your DockerHub account or to your private Docker registry. 

4. __Create the secrets:__ You need to create the secrets required by the polling container to connect to Azure DevOps. You can use the file `k8s-devops/secrets.yaml` as a template. You need to replace the placeholders with the actual values. The PAT token needs to have Full Access to your Azure DevOps organization.

5. __Deploy Polling Container:__
```bash
kubectl apply -f rbac.yaml
kubectl apply -f secrets.yaml
kubectl apply -f pod.yaml
```

6. __Monitoring:__ Once the polling container is up and running, it will start monitoring Azure DevOps and automatically scale agents as needed.

## Considerations

- If you need more than one agent model, you can modify the namespace of the agents in the file `k8s-devops/polling.py`, update all yamls to the new defined namespace with a new docker container image name, create a new secret for each agent model and then deploy the polling container again.
- Ensure the AKS cluster has enough resources to accommodate the anticipated workload.
- Regularly monitor logs and metrics to ensure the solution operates as intended.