import json
import os
import re
import sys
from pathlib import Path

import got
import openai
import requests
from ipykernel.ipkernel import IPythonKernel

from .configs import (
    SERVER_LOGIN_NUM_ATTEMPTS,
    SERVER_TIMEOUT,
    server_sub_url,
)
from .errors import GothubKernelError
from .super_king import super_king_debug
from .utils import firebase

# Model
DEFAULT_SYSTEM_PROMPT = """\
"""

DEFAULT_CHAT_MESSAGES_START = (
    {
        "role": "system",
        "content": DEFAULT_SYSTEM_PROMPT,
    },
)


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

        self.gothub_api_key = os.environ["GOTHUB_API_KEY"]

        for _ in range(SERVER_LOGIN_NUM_ATTEMPTS):
            try:
                my_firebase_password_response = requests.get(
                    server_sub_url("my-firebase-password"),
                    headers={
                        "GotHub-API-Key": self.gothub_api_key,
                    },
                    timeout=SERVER_TIMEOUT,
                )
                my_firebase_password_response.raise_for_status()
                my_firebase_password_json = my_firebase_password_response.json()
                break
            except requests.exceptions.Timeout:
                pass

        self.user_id = my_firebase_password_json["id"]
        self.user_name = my_firebase_password_json["name"]
        self.user_email = my_firebase_password_json["email"]
        self.user_password = my_firebase_password_json["password"]

        openai.api_key = my_firebase_password_json["OPENAI_API_KEY"]

        self.firebase_user = firebase.auth.sign_in_with_email_and_password(
            self.user_email,
            self.user_password,
        )

        self.OPENAI_MODEL_TO_BE_SET = got.DEFAULT_OPENAI_MODEL
        self.chat_messages = list(DEFAULT_CHAT_MESSAGES_START)

    def __print(self, obj):
        stream_content = {
            "name": "stdout",
            "text": str(obj),
        }
        self.send_response(
            self.iopub_socket,
            "stream",
            stream_content,
        )

    def __print_error(self, obj):
        stream_content = {
            "name": "stderr",
            "text": str(obj),
        }
        self.send_response(
            self.iopub_socket,
            "stream",
            stream_content,
        )

    def __print_markdown(self, markdown: str):
        stream_content = {
            "metadata": {},
            "data": {
                "text/markdown": markdown,
            },
        }
        self.send_response(
            self.iopub_socket,
            "display_data",
            stream_content,
        )

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
                who_am_i_response = requests.get(
                    server_sub_url("whoami"),
                    headers={
                        "GotHub-API-Key": self.gothub_api_key,
                    },
                    timeout=SERVER_TIMEOUT,
                )
                who_am_i_response.raise_for_status()
                who_am_i = who_am_i_response.json()
                who_am_i_pretty = json.dumps(who_am_i, indent=4)

                self.__print_markdown(f"```json\n{who_am_i_pretty}\n```")

                return super().do_execute(
                    "None",
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

            super_king_debug_regex = r"^\s*super king debug\s*$"
            if re.match(super_king_debug_regex, code):
                super_king_debug(self)

                return super().do_execute(
                    "None",
                    silent,
                    store_history,
                    user_expressions,
                    allow_stdin,
                )

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

            self.__print_markdown(f"**ChatGPT {got.OPENAI_MODEL}:**")

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

                self.__print(output)
                all_outputs.append(output)

            final_output = "".join(all_outputs)

            self.chat_messages = self.chat_messages + [
                {
                    "role": "assistant",
                    "content": final_output,
                },
            ]

            firebase.firestore.collection("chat_records").document(self.user_id).update(
                {
                    "num_chats": firebase.firestore.Increment(1),
                    "num_characters": firebase.firestore.Increment(len(final_output)),
                },
                self.firebase_user["idToken"],
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
