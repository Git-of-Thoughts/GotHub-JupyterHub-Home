from pathlib import Path

from dotenv import dotenv_values
from ipykernel.kernelbase import Kernel

# Home directory of the user
HOME_PATH = Path.home()
KEYS_PATH = HOME_PATH / "_keys"
DOTENV_VALUES = dotenv_values(KEYS_PATH)


class ChatGptKernel(Kernel):
    """
    Copied from
    https://ipython.readthedocs.io/en/3.x/development/wrapperkernels.html
    and
    https://jupyter-client.readthedocs.io/en/latest/wrapperkernels.html
    """

    implementation = "ChatGPT"
    implementation_version = "1.0"
    language = "chatgpt"
    language_version = "0.1"
    language_info = {
        "name": "Any text",
        "mimetype": "text/plain",
        "file_extension": ".txt",
    }
    banner = "ChatGPT Kernel"

    def do_execute(
        self,
        code,
        silent,
        store_history=True,
        user_expressions=None,
        allow_stdin=False,
    ):
        if not silent:
            stream_content = {
                "name": "stdout",
                "text": str(DOTENV_VALUES.get("OPENAI_API_KEY")),
            }
            self.send_response(
                self.iopub_socket,
                "stream",
                stream_content,
            )

        return {
            "status": "ok",
            # The base class increments the execution count
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }
