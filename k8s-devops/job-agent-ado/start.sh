#!/bin/bash
set -e

if [ -z "$ADO_URL" ] || [ -z "$ADO_PAT" ] || [ -z "$ADO_AGENT_NAME" ] || [ -z "$ADO_POOL" ]; then
    echo "Error: Env variables needed (ADO_URL, ADO_PAT, ADO_AGENT_NAME, ADO_POOL)!"
    exit 1
fi

# Agent config
./config.sh --unattended \
  --agent "${ADO_AGENT_NAME}" \
  --url "${ADO_URL}" \
  --auth PAT \
  --token "${ADO_PAT}" \
  --pool "${ADO_POOL}" \
  --replace \
  --acceptTeeEula

# Run agent as ephemeral
./run.sh --once