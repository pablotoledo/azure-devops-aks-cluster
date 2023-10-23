import os
import yaml
import requests
import base64
from kubernetes import client, config
import time
from tabulate import tabulate
from termcolor import colored

# K8s configuration
MAX_REPLICAS = int(os.environ.get("MAX_REPLICAS", 5))
NAMESPACE = 'devops-k8s-ns'
LABEL_SELECTOR = "role=ado-agent"
config.load_incluster_config()
v1 = client.AppsV1Api()

# Azure DevOps configuration
ADO_NAME = os.environ.get('ADO_NAME', 'default_value_if_not_provided')
ADO_PAT = os.environ.get('ADO_PAT', 'default_value_if_not_provided')
POOL_NAME = os.environ.get('ADO_POOL', 'default_value_if_not_provided')
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
    job_spec = load_yaml_file("job-agent.yaml")
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
        print("Creating a new job...")
    if current_jobs + jobs_to_create >= MAX_REPLICAS:
        print("No more jobs will be created. The maximum number of replicas has been reached.")
        print(f"Current jobs: {current_jobs} - Queued jobs: {queued_jobs_count} - Max replicas: {MAX_REPLICAS}")
        
def remove_offline_agents(pool_id):
    headers = {
        "Authorization": f"Basic {base64.b64encode(bytes(':' + ADO_PAT, 'utf-8')).decode('ascii')}"
    }

    # 1. Get a list of all agents in the pool
    url = f"https://dev.azure.com/{ADO_NAME}/_apis/distributedtask/pools/{pool_id}/agents"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    agents = response.json()["value"]

    # 2. Filter those agents that are offline
    offline_agents = [agent for agent in agents if agent["status"] == "offline" and agent["name"].startswith("ado-agent-")]

    # 3. Remove offline agents
    for agent in offline_agents:
        delete_url = f"https://dev.azure.com/{ADO_NAME}/_apis/distributedtask/pools/{pool_id}/agents/{agent['id']}?api-version=6.0"
        delete_response = requests.delete(delete_url, headers=headers)
        print(f"Removing offline agent: {agent['name']} - Response Status:({delete_response.status_code})")

while True:
    print("-----------------------------------------------------------------------------------------------------------------")
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    # Step 0: Get info from Azure DevOps
    pool_id = get_pool_id()
    running_jobs_data = get_running_jobs_for_pool(pool_id)

    # Step 1: Print the jobs
    running_jobs, queued_jobs, summary = analyze_jobs(running_jobs_data)
    
    # Step 2: Analyze the jobs
    queued_jobs_count = len(queued_jobs)

    # Step 3: Decision logic
    if queued_jobs_count > 0:
        scale_horizontally(queued_jobs_count)
    else:
        print("The queue is empty. No action required.")
    
    # Step 4: Remove offline agents
    remove_offline_agents(pool_id)

    # Wait before the next polling
    time.sleep(POLLING_INTERVAL)