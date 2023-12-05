import re
import sys
import traceback
from pathlib import Path

import openai
from dotenv import dotenv_values
from ipykernel.ipkernel import IPythonKernel
from ipykernel.kernelbase import Kernel

# Model
DEFAULT_MODEL = "gpt-4"
DEFAULT_SYSTEM_PROMPT = """\
"""


# Home directory of the user
HOME_PATH = Path.home()
DOTENV_PATH = HOME_PATH / "__keys__"
DOTENV_VALUES = dotenv_values(DOTENV_PATH)
openai.api_key = DOTENV_VALUES["OPENAI_API_KEY"]


class ChatGptKernel(IPythonKernel):
    """
    Copied from
    https://ipython.readthedocs.io/en/3.x/development/wrapperkernels.html
    and
    https://jupyter-client.readthedocs.io/en/latest/wrapperkernels.html
    """

    implementation = "ChatGPT"
    implementation_version = "1.0"
    language = "python"
    language_version = sys.version.split()[0]
    language_info = {
        "name": "python",
        "mimetype": "text/x-python",
        "file_extension": ".py",
    }
    banner = "ChatGPT Kernel"

    def do_execute(
        self,
        code: str,
        silent,
        store_history=True,
        user_expressions=None,
        allow_stdin=False,
    ):
        as_code_regex = r"^\s*as\s+(code|py|python)\s+"

        match = re.match(as_code_regex, code)
        if match:
            code = code[match.end() :]
            return super().do_execute(
                code,
                silent,
                store_history,
                user_expressions,
                allow_stdin,
            )

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

            except openai.error.AuthenticationError as e:
                return super().do_execute(
                    f"raise Exception({repr(e)})",
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

            except Exception as e:
                return super().do_execute(
                    f"raise Exception({repr(e)})",
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

        return {
            "status": "ok",
            # The base class increments the execution count
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }
