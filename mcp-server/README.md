STEP: current dir
cd /mnt/c/Users/DKGOSQLDT/gpu-enabled-minikube/ts-products-projects/ts-mcp-apps/ts-mcp-k8s/mcp-server



STEP: create / activate env
    env name:.mcpservervenv

    python3 -m venv .mcpservervenv

    source .mcpservervenv/bin/activate

    python3 -m pip install --upgrade pip

    python3 -m pip install -r mcp-server/requirements.txt

    python3 -m pip install -r mcp-chat-ui/requirements.txt



python3 server.py
    cd mcp-server 

    npx @modelcontextprotocol/inspector \
        .mcpservervenv/bin/python \
        server.py
    or 
    python3 server.py

STEP: start client ui
    streamlit run app.py


Testing