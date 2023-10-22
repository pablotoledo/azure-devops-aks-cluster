FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    jq \
    tar \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Crear un usuario no-root llamado "agentuser"
RUN useradd -ms /bin/bash agentuser

ARG AGENT_DOWNLOAD_URL=https://vstsagentpackage.azureedge.net/agent/3.227.2/vsts-agent-linux-x64-3.227.2.tar.gz

WORKDIR /azdo-agent

RUN curl -L ${AGENT_DOWNLOAD_URL} | tar -zx

COPY start.sh /azdo-agent/start.sh

RUN chmod +x start.sh
RUN chown -R agentuser:agentuser /azdo-agent

# Ejecuta el script para instalar las dependencias faltantes
RUN ./bin/installdependencies.sh


# Cambiar al usuario "agentuser"
USER agentuser

# El script de inicio se ejecutará cuando se inicie el contenedor.
CMD ["./start.sh"]
