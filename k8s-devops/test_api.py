# Con esta clase busco hacer ingeniería inversa de la API de Azure DevOps
import requests
import os
import base64
import json

def get_pool_id(pool_name):
    headers = {
        "Authorization": f"Basic {base64.b64encode(bytes(':' + pat, 'utf-8')).decode('ascii')}"
    }

    url = f"https://dev.azure.com/{organization_name}/_apis/distributedtask/pools?poolName={pool_name}&api-version=6.0"
    response = requests.get(url, headers=headers)
    response.raise_for_status()  
    data = response.json()

    # Retorna el ID del agent pool
    return data["value"][0]["id"]

def get_queues_for_pool(pool_id):
    headers = {
        "Authorization": f"Basic {base64.b64encode(bytes(':' + pat, 'utf-8')).decode('ascii')}"
    }

    url = f"https://dev.azure.com/{organization_name}/{project_name}/_apis/distributedtask/queues?poolIds={pool_id}&api-version=7.1-preview.1"
    response = requests.get(url, headers=headers)
    response.raise_for_status()  
    data = response.json()

    # Retorna los detalles de las colas para el pool de agentes
    return data

def get_running_jobs_for_pool(pool_id):
    headers = {
        "Authorization": f"Basic {base64.b64encode(bytes(':' + pat, 'utf-8')).decode('ascii')}"
    }

    url = f"https://dev.azure.com/{organization_name}/_apis/distributedtask/pools/{pool_id}/jobrequests"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    # Filtrar trabajos que estén en ejecución (no tienen la propiedad "result")
    running_jobs = [job for job in data["value"] if "result" not in job]

    return running_jobs

def analyze_jobs(jobs_data):
    # Lists to store job details
    running_jobs = []
    queued_jobs = []

    # Iterating over each job to analyze its status and assigned agent
    for job in jobs_data:
        job_details = {
            "requestId": job["requestId"],
            "jobName": job["owner"]["name"],
            "queueTime": job["queueTime"],
            "status": "In Execution" if "lockedUntil" in job else "Queued"
        }

        # Check if the job has an agent assigned
        if "reservedAgent" in job:
            job_details["agent"] = job["reservedAgent"]["name"]
            running_jobs.append(job_details)
        else:
            job_details["agent"] = "Not Assigned"
            queued_jobs.append(job_details)

    # Summary of the queue
    summary = {
        "totalJobs": len(jobs_data),
        "runningJobsCount": len(running_jobs),
        "queuedJobsCount": len(queued_jobs)
    }

    return running_jobs, queued_jobs, summary

def remove_offline_agents(pool_id):
    headers = {
        "Authorization": f"Basic {base64.b64encode(bytes(':' + pat, 'utf-8')).decode('ascii')}"
    }

    # 1. Obtener una lista de todos los agentes en el pool
    url = f"https://dev.azure.com/{organization_name}/_apis/distributedtask/pools/{pool_id}/agents"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    agents = response.json()["value"]

    # 2. Filtrar aquellos agentes que estén offline
    offline_agents = [agent for agent in agents if agent["status"] == "offline" and agent["name"].startswith("ado-agent-")]


    # 3. Eliminar los agentes offline
    for agent in offline_agents:
        delete_url = f"https://dev.azure.com/{organization_name}/_apis/distributedtask/pools/{pool_id}/agents/{agent['id']}?api-version=6.0"
        delete_response = requests.delete(delete_url, headers=headers)
        if delete_response.status_code == 200:
            print(f"Removed offline agent: {agent['name']}")

# Carga las variables de entorno
organization_name = os.environ.get('ADO_NAME', 'default_value_if_not_provided')
project_name = os.environ.get('ADO_PROJECT', 'default_value_if_not_provided')
pat = os.environ.get('ADO_PAT', 'default_value_if_not_provided')
pool_name = "k8s-cloud"

# Obtener ID del pool basado en el nombre
pool_id = get_pool_id(pool_name)
print(f"ID para el pool {pool_name}: {pool_id}")

# Obtener las colas para el ID del pool
queues_data = get_queues_for_pool(pool_id)
print(queues_data)

# Obtener trabajos en ejecución para el ID del pool
running_jobs_data = get_running_jobs_for_pool(pool_id)
print(f"Trabajos en ejecución para el pool {pool_name}:")
print(running_jobs_data)

# Assuming running_jobs_data is the output from get_running_jobs_for_pool
running_jobs_data = get_running_jobs_for_pool(pool_id)

running_jobs, queued_jobs, summary = analyze_jobs(running_jobs_data)
print("Running Jobs:", running_jobs)
print("Queued Jobs:", queued_jobs)
print("Summary:", summary)

# Eliminar agentes offline
remove_offline_agents(pool_id)


