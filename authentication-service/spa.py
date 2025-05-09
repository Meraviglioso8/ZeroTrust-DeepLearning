from http.server import SimpleHTTPRequestHandler, HTTPServer

def run_server(port: int = 6969) -> None:
    """
    Start a simple HTTP server to serve static files from the current directory.

    Args:
        port (int): The port to bind the HTTP server to.
    """
    handler = SimpleHTTPRequestHandler
    with HTTPServer(('', port), handler) as httpd:
        print(f"Serving static files at http://localhost:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
