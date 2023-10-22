import os
import yaml
import requests
import base64
from kubernetes import client, config
import time
from tabulate import tabulate
from termcolor import colored

# Configuración de Kubernetes
MAX_REPLICAS = 10
NAMESPACE = 'devops-k8s-ns'
LABEL_SELECTOR = "role=ado-agent"
config.load_incluster_config()
v1 = client.AppsV1Api()

# Configuración de Azure DevOps
ADO_NAME = os.environ.get('ADO_NAME', 'default_value_if_not_provided')
ADO_PROJECT = os.environ.get('ADO_PROJECT', 'default_value_if_not_provided')
ADO_PAT = os.environ.get('ADO_PAT', 'default_value_if_not_provided')
POOL_NAME = "k8s-cloud"
POLLING_INTERVAL = 60  # En segundos


def get_pool_id():
    headers = {
        "Authorization": f"Basic {base64.b64encode(bytes(':' + ADO_PAT, 'utf-8')).decode('ascii')}"
    }

    url = f"https://dev.azure.com/{ADO_NAME}/_apis/distributedtask/pools?poolName={POOL_NAME}&api-version=6.0"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data["value"][0]["id"]


def get_running_jobs_for_pool(pool_id):
    headers = {
        "Authorization": f"Basic {base64.b64encode(bytes(':' + ADO_PAT, 'utf-8')).decode('ascii')}"
    }

    url = f"https://dev.azure.com/{ADO_NAME}/_apis/distributedtask/pools/{pool_id}/jobrequests"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    running_jobs = [job for job in data["value"] if "result" not in job]
    return running_jobs


def analyze_jobs(jobs_data):
    queued_jobs = [job for job in jobs_data if "reservedAgent" not in job]
    return len(queued_jobs)


def get_current_job_count():
    jobs = client.BatchV1Api().list_namespaced_job(NAMESPACE, label_selector=LABEL_SELECTOR)
    running_jobs = [job for job in jobs.items if job.status.active]
    return len(running_jobs)

def analyze_jobs(jobs_data):
    # Lists to store job details
    running_jobs = []
    queued_jobs = []

    # Iterating over each job to analyze its status and assigned agent
    for job in jobs_data:
        job_details = {
            "requestId": job["requestId"],
            "jobName": "{:.0f}".format(float(job["owner"]["name"])),
            "repoName": job["definition"]["name"],
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

    # Print the results in a colored table
    print_jobs_table(running_jobs, queued_jobs)

    return running_jobs, queued_jobs, summary


def print_jobs_table(running_jobs, queued_jobs):
    # Merge the lists and sort them by queue time
    all_jobs = sorted(running_jobs + queued_jobs, key=lambda x: x["queueTime"])

    # Color the rows based on the status
    colored_rows = []
    for job in all_jobs:
        if job["status"] == "In Execution":
            colored_rows.append([
                colored(job["requestId"], 'green'),
                colored(job["jobName"], 'green'),
                colored(job["repoName"], 'green'),
                colored(job["queueTime"], 'green'),
                colored(job["status"], 'green'),
                colored(job["agent"], 'green')
            ])
        elif job["status"] == "Queued":
            colored_rows.append([
                colored(job["requestId"], 'yellow'),
                colored(job["jobName"], 'yellow'),
                colored(job["repoName"], 'grey'),
                colored(job["queueTime"], 'yellow'),
                colored(job["status"], 'yellow'),
                colored(job["agent"], 'yellow')
            ])
        else:
            colored_rows.append([
                colored(job["requestId"], 'grey'),
                colored(job["jobName"], 'grey'),
                colored(job["repoName"], 'grey'),
                colored(job["queueTime"], 'grey'),
                colored(job["status"], 'grey'),
                colored(job["agent"], 'grey')
            ])

    # Print the table
    headers = ["Request ID", "Job Name", "Repo Name", "Queue Time", "Status", "Agent"]
    print(tabulate(colored_rows, headers=headers, tablefmt='grid'))

def create_k8s_job():
    def load_yaml_file(relative_path):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        yaml_path = os.path.join(script_dir, relative_path)
        
        with open(yaml_path, 'r') as file:
            return yaml.safe_load(file)
        
    api_instance = client.BatchV1Api()
    job_spec = load_yaml_file("pod-agent.yaml")
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(generate_name="ado-agent-"),
        spec=job_spec["spec"]
    )
    api_instance.create_namespaced_job(namespace=NAMESPACE, body=job)

def scale_horizontally(queued_jobs_count):
    current_jobs = get_current_job_count()
    jobs_to_create = min(queued_jobs_count, MAX_REPLICAS - current_jobs)
    
    for _ in range(jobs_to_create):
        create_k8s_job()
        print("Job creado.")
    
    if current_jobs + jobs_to_create >= MAX_REPLICAS:
        print("Ya se ha alcanzado el máximo de replicas. No se crearán más jobs.")
        
def remove_offline_agents(pool_id):
    headers = {
        "Authorization": f"Basic {base64.b64encode(bytes(':' + ADO_PAT, 'utf-8')).decode('ascii')}"
    }

    # 1. Obtener una lista de todos los agentes en el pool
    url = f"https://dev.azure.com/{ADO_NAME}/_apis/distributedtask/pools/{pool_id}/agents"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    agents = response.json()["value"]

    # 2. Filtrar aquellos agentes que estén offline
    offline_agents = [agent for agent in agents if agent["status"] == "offline" and agent["name"].startswith("ado-agent-")]

    # 3. Eliminar los agentes offline
    for agent in offline_agents:
        delete_url = f"https://dev.azure.com/{ADO_NAME}/_apis/distributedtask/pools/{pool_id}/agents/{agent['id']}?api-version=6.0"
        delete_response = requests.delete(delete_url, headers=headers)
        if delete_response.status_code == 200:
            print(f"Removed offline agent: {agent['name']}")

while True:
    # Paso 0: Obtener datos de Azure DevOps
    print("-----------------------------------------------------------------------------------------------------------------")
    pool_id = get_pool_id()
    running_jobs_data = get_running_jobs_for_pool(pool_id)

    # Paso 1: Imprimimos
    running_jobs, queued_jobs, summary = analyze_jobs(running_jobs_data)
    
    # Paso 2: Analizar trabajos
    queued_jobs_count = len(queued_jobs)

    # Paso 3: Lógica de decisión
    if queued_jobs_count > 0:
        scale_horizontally(queued_jobs_count)
    else:
        #scale_down()
        print("No hay acciones con nuevos Jobs a realizar.")
    
    # Paso 4: Eliminar agentes offline
    remove_offline_agents(pool_id)

    # Esperar antes de la siguiente revisión
    time.sleep(POLLING_INTERVAL)