FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    jq \
    tar \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

ARG AGENT_DOWNLOAD_URL=https://vstsagentpackage.azureedge.net/agent/3.227.2/vsts-agent-linux-x64-3.227.2.tar.gz

WORKDIR /azdo-agent

RUN curl -L ${AGENT_DOWNLOAD_URL} | tar -zx

COPY start.sh /azdo-agent/start.sh

# El script de inicio se ejecutará cuando se inicie el contenedor.
CMD ["./start.sh"]
