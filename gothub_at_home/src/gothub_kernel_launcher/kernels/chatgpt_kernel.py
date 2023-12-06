import html
import re
import sys
from pathlib import Path

import got
import openai
from ipykernel.ipkernel import IPythonKernel
from yaml import safe_load

from .errors import GothubKernelError

# Model
DEFAULT_SYSTEM_PROMPT = """\
"""


OPENAI_MODEL = got.DEFAULT_OPENAI_MODEL


# Home directory of the user
HOME_PATH = Path.home()
KEYS_YAML_PATH = HOME_PATH / "__keys__.yaml"


class KeysYamlNotFoundError(GothubKernelError):
    """Raised when __keys__.yaml is not found in $HOME."""

    pass


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
        try:
            if code.strip() == "":
                # We could early return
                pass

            if not KEYS_YAML_PATH.exists():
                raise KeysYamlNotFoundError(
                    "Please set a valid OPENAI_API_KEY in $HOME/__keys__.yaml.",
                )

            keys_yaml_values = safe_load(KEYS_YAML_PATH.read_text()) or {}
            openai.api_key = keys_yaml_values.get("OPENAI_API_KEY")

            global OPENAI_MODEL

            as_code_regex = r"^\s*as\s+(code|py|python)\s+"

            if as_code_match := re.match(as_code_regex, code):
                code = code[as_code_match.end() :]

                # ! This is pretty important
                got.OPENAI_MODEL = OPENAI_MODEL

                return super().do_execute(
                    code,
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

            with_gpt_3_5_regex = r"^\s*with\s+(gpt|gpt-)3.5\s*"
            with_gpt_4_regex = r"^\s*with\s+(gpt|gpt-)4\s*"

            if with_gpt_3_5_match := re.match(with_gpt_3_5_regex, code):
                code = code[with_gpt_3_5_match.end() :]

                OPENAI_MODEL = "gpt-3.5-turbo"
                got.OPENAI_MODEL = OPENAI_MODEL

                result = self.do_execute(
                    code,
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

                OPENAI_MODEL = got.DEFAULT_OPENAI_MODEL
                # ! You can't do this
                # got.OPENAI_MODEL = OPENAI_MODEL

                return result

            if with_gpt_4_match := re.match(with_gpt_4_regex, code):
                code = code[with_gpt_4_match.end() :]

                OPENAI_MODEL = "gpt-4"
                got.OPENAI_MODEL = OPENAI_MODEL

                result = self.do_execute(
                    code,
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

                OPENAI_MODEL = got.DEFAULT_OPENAI_MODEL
                # ! You can't do this
                # got.OPENAI_MODEL = OPENAI_MODEL

                return result

            if not silent:
                stream_content = {
                    "metadata": {},
                    "data": {
                        "text/markdown": f"""
<b>ChatGPT {OPENAI_MODEL}:</b>
<style>
details {{
    user-select: none;
}}
details>summary span.icon {{
    width: 24px;
    height: 24px;
    transition: all 0.3s;
    margin-left: auto;
}}
details[open] summary span.icon {{
    transform: rotate(180deg);
}}
summary {{
    cursor: pointer;
}}
summary::-webkit-details-marker {{
    display: none;
}}
</style>
<details>
    <summary>
        You said:
        <span class="icon">👇</span>
    </summary>
""",
                    },
                }
                self.send_response(
                    self.iopub_socket,
                    "display_data",
                    stream_content,
                )

                stream_content = {
                    "metadata": {},
                    "data": {
                        "text/markdown": f"""
{code}
""",
                    },
                }
                self.send_response(
                    self.iopub_socket,
                    "display_data",
                    stream_content,
                )

                stream_content = {
                    "metadata": {},
                    "data": {
                        "text/markdown": """
</details>
""",
                    },
                }
                self.send_response(
                    self.iopub_socket,
                    "display_data",
                    stream_content,
                )

                response = openai.ChatCompletion.create(
                    model=OPENAI_MODEL,
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
            msg = "\n\nPlease set a valid OPENAI_API_KEY in $HOME/__keys__.yaml."
            return super().do_execute(
                f"raise Exception({repr(repr(e))} + {repr(msg)})",
                silent,
                store_history,
                user_expressions,
                allow_stdin,
            )

        except Exception as e:
            return super().do_execute(
                f"raise Exception({repr(repr(e))})",
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
