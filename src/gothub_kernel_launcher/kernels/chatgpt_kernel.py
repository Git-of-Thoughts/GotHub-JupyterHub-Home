import os
import re
import sys
from pathlib import Path

import got
import openai
import requests
from ipykernel.ipkernel import IPythonKernel
from yaml import safe_load

from .errors import GothubKernelError

# Server
SERVER_URL = "https://gothub-flask.vercel.app"
SERVER_WHO_AM_I_URL = f"{SERVER_URL}/whoami"
SERVER_MY_FIREBASE_PASSWORD_URL = f"{SERVER_URL}/my-firebase-password"


# Model
DEFAULT_SYSTEM_PROMPT = """\
"""

DEFAULT_CHAT_MESSAGES_START = (
    {
        "role": "system",
        "content": DEFAULT_SYSTEM_PROMPT,
    },
)


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.OPENAI_MODEL_TO_BE_SET = got.DEFAULT_OPENAI_MODEL
        self.chat_messages = list(DEFAULT_CHAT_MESSAGES_START)

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

            print_account_regex = r"^\s*print\s+account\s*$"
            if re.match(print_account_regex, code):
                gothub_api_key = os.environ["GOTHUB_API_KEY"]
                who_am_i_response = requests.get(
                    SERVER_WHO_AM_I_URL,
                    headers={
                        "GotHub-API-Key": gothub_api_key,
                    },
                )
                who_am_i_response.raise_for_status()
                who_am_i = who_am_i_response.json()

                return self.do_execute(
                    f"as code: {who_am_i}",
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

            if not KEYS_YAML_PATH.exists():
                raise KeysYamlNotFoundError(
                    "Please set a valid OPENAI_API_KEY in $HOME/__keys__.yaml.",
                )

            keys_yaml_values = safe_load(KEYS_YAML_PATH.read_text()) or {}
            openai.api_key = keys_yaml_values.get("OPENAI_API_KEY")

            # ! This is pretty important
            got.OPENAI_MODEL = self.OPENAI_MODEL_TO_BE_SET

            as_code_regex = r"^\s*as\s+(?:code|py|python)(:|\s*$|\s+)"

            if as_code_match := re.match(as_code_regex, code):
                code = code[as_code_match.end(1) :]

                return super().do_execute(
                    code,
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

            as_new_chat_regex = r"^\s*as\s+new\s+chat(:|\s*$|\s+)"

            if as_new_chat_match := re.match(as_new_chat_regex, code):
                code = code[as_new_chat_match.end(1) :]

                self.chat_messages = list(DEFAULT_CHAT_MESSAGES_START)

                result = self.do_execute(
                    code,
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

                return result

            with_gpt_3_5_regex = r"^\s*with\s+(?:gpt|gpt-)3.5(:|\s*$|\s+)"
            with_gpt_4_regex = r"^\s*with\s+(?:gpt|gpt-)4(:|\s*$|\s+)"

            if with_gpt_3_5_match := re.match(with_gpt_3_5_regex, code):
                code = code[with_gpt_3_5_match.end(1) :]

                self.OPENAI_MODEL_TO_BE_SET = "gpt-3.5-turbo"
                got.OPENAI_MODEL = self.OPENAI_MODEL_TO_BE_SET

                result = self.do_execute(
                    code,
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

                self.OPENAI_MODEL_TO_BE_SET = got.DEFAULT_OPENAI_MODEL
                # ! You can't do this (probably due to async)
                # got.OPENAI_MODEL = self.OPENAI_MODEL_TO_BE_SET

                return result

            if with_gpt_4_match := re.match(with_gpt_4_regex, code):
                code = code[with_gpt_4_match.end(1) :]

                self.OPENAI_MODEL_TO_BE_SET = "gpt-4"
                got.OPENAI_MODEL = self.OPENAI_MODEL_TO_BE_SET

                result = self.do_execute(
                    code,
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

                self.OPENAI_MODEL_TO_BE_SET = got.DEFAULT_OPENAI_MODEL
                # ! You can't do this (probably due to async)
                # got.OPENAI_MODEL = self.OPENAI_MODEL_TO_BE_SET

                return result

            if silent:
                return super().do_execute(
                    "None",
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

            stream_content = {
                "metadata": {},
                "data": {
                    "text/markdown": f"**ChatGPT {got.OPENAI_MODEL}:**",
                },
            }
            self.send_response(
                self.iopub_socket,
                "display_data",
                stream_content,
            )

            self.chat_messages = self.chat_messages + [
                {
                    "role": "user",
                    "content": code,
                },
            ]

            response = openai.ChatCompletion.create(
                model=got.OPENAI_MODEL,
                messages=self.chat_messages,
                stream=True,
            )

            all_outputs = []
            for res in response:
                output = "".join(
                    [
                        choice["delta"]["content"]
                        if "content" in choice["delta"]
                        else ""
                        for choice in res["choices"]
                    ]
                )

                all_outputs.append(output)

                stream_content = {
                    "name": "stdout",
                    "text": output,
                }
                self.send_response(
                    self.iopub_socket,
                    "stream",
                    stream_content,
                )

            self.chat_messages = self.chat_messages + [
                {
                    "role": "assistant",
                    "content": "".join(all_outputs),
                },
            ]

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

        return super().do_execute(
            "None",
            silent,
            store_history,
            user_expressions,
            allow_stdin,
        )

        return {
            "status": "ok",
            # The base class increments the execution count
            # ! But somehow it's not increasing unless "as code" is used
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }
