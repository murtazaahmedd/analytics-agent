from truemetric.composition import build_services, config_from_env
from truemetric.mcp_servers.semantic_layer.server import create_server

if __name__ == "__main__":
    create_server(build_services(config_from_env()).semantic).run("stdio")
