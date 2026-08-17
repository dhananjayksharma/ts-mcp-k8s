# START this APP:
### STEP: current dir
    cd /mnt/c/Users/DKGOSQLDT/gpu-enabled-minikube/ts-products-projects/ts-mcp-apps/ts-mcp-k8s/mcp-server

### start minikube
    minikube start --driver=docker --container-runtime=docker --gpus=all --cpus=6 --memory=6144 --disk-size=40g --profile=gpu-cpu-lab --nodes=3

### export ENV
    source .env

### STEP: create / activate env
    env name:.mcpservervenv

    python3 -m venv .mcpservervenv

    source .mcpservervenv/bin/activate

    python3 -m pip install --upgrade pip 
    python3 -m pip install -r mcp-server/requirements.txt

    python3 -m pip install -r mcp-chat-ui/requirements.txt
 
    cd mcp-server
    npx @modelcontextprotocol/inspector \
        .mcpservervenv/bin/python \
        server.py
    or 
    python3 server.py

### STEP: start client ui
    cd mcp-chat-ui/ui
    streamlit run app.py

