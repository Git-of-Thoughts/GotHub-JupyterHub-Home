from pathlib import Path

import openai
from dotenv import dotenv_values
from ipykernel.kernelbase import Kernel

# Model
DEFAULT_MODEL = "gpt-4"
DEFAULT_SYSTEM_PROMPT = """\
"""


# Home directory of the user
HOME_PATH = Path.home()
DOTENV_PATH = HOME_PATH / "_keys"
DOTENV_VALUES = dotenv_values(DOTENV_PATH)
openai.api_key = DOTENV_VALUES["OPENAI_API_KEY"]


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
            try:
                response = openai.ChatCompletion.create(
                    model=DEFAULT_MODEL,
                    messages=[  # TODO use system messages
                        {
                            "role": "system",
                            "content": DEFAULT_SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": code,
                        },
                    ],
                    stream=True,
                )
                for res in response:
                    output = "".join(
                        [
                            choice["delta"]["content"]
                            if "content" in choice["delta"]
                            else ""
                            for choice in res["choices"]
                        ]
                    )
                    stream_content = {
                        "name": "stdout",
                        "text": output,
                    }
                    self.send_response(
                        self.iopub_socket,
                        "stream",
                        stream_content,
                    )

            except Exception as err:
                stream_content = {
                    "name": "stderr",
                    "text": f"{err}",
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
