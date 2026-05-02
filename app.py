from student_analysis.web import create_app
import os
import socket
import threading
import webbrowser


app = create_app()


def find_free_port(start: int = 8765) -> int:
    for port in range(start, start + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("找不到可用端口")


if __name__ == "__main__":
    port = find_free_port(int(os.environ.get("STUDENT_ANALYSIS_PORT", "8765")))
    if os.environ.get("STUDENT_ANALYSIS_NO_BROWSER") != "1":
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
