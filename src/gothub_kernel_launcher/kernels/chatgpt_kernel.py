import json
import os
import re
import sys
from pathlib import Path

import got
import requests
from google.cloud.firestore import (
    SERVER_TIMESTAMP as FirestoreServerTimestamp,
)
from google.cloud.firestore import (
    Increment as FirestoreIncrement,
)
from ipykernel.ipkernel import IPythonKernel
from openai import OpenAI

from .configs import (
    SERVER_LOGIN_NUM_ATTEMPTS,
    SERVER_TIMEOUT,
    server_sub_url,
)
from .errors import PleaseUpgradePlan
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

        firebase.user_id = my_firebase_password_json["id"]
        firebase.user_name = my_firebase_password_json["name"]
        firebase.user_email = my_firebase_password_json["email"]
        firebase.user_password = my_firebase_password_json["password"]

        got.openai_client = OpenAI(
            api_key=my_firebase_password_json["OPENAI_API_KEY"],
        )
        got.together_client = OpenAI(
            api_key=my_firebase_password_json["TOGETHER_API_KEY"],
            base_url="https://api.together.xyz/v1",
        )

        firebase.firebase_user = firebase.auth.sign_in_with_email_and_password(
            firebase.user_email,
            firebase.user_password,
        )

        self.OPENAI_MODEL_TO_BE_SET = got.DEFAULT_OPENAI_MODEL
        self.chat_messages = list(DEFAULT_CHAT_MESSAGES_START)

    def _gothub_print(self, obj):
        stream_content = {
            "name": "stdout",
            "text": str(obj),
        }
        self.send_response(
            self.iopub_socket,
            "stream",
            stream_content,
        )

    def _gothub_print_error(self, obj):
        stream_content = {
            "name": "stderr",
            "text": str(obj),
        }
        self.send_response(
            self.iopub_socket,
            "stream",
            stream_content,
        )

    def _gothub_print_markdown(self, markdown: str):
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

    def _gothub_do_execute_with_model(
        self,
        code: str,
        match: re.Match,
        model: str,
        *,
        silent,
        store_history,
        user_expressions,
        allow_stdin,
    ):
        code = code[match.end(1) :]

        self.OPENAI_MODEL_TO_BE_SET = model
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
        got.OPENAI_MODEL = self.OPENAI_MODEL_TO_BE_SET

        return result

    def _gothub_use_model_chat(self, code):
        self._gothub_print_markdown(f"**{got.get_model_name()}:**")

        self.chat_messages = self.chat_messages + [
            {
                "role": "user",
                "content": code,
            },
        ]

        response = got.get_client().chat.completions.create(
            model=got.OPENAI_MODEL,
            messages=self.chat_messages,
            stream=True,
            **got.get_kwargs_for_chat_completions_create(),
        )

        all_outputs = []
        for res in response:
            output = "".join(
                [choice.delta.content or "" for choice in res.choices],
            )

            self._gothub_print(output)
            all_outputs.append(output)

        final_output = "".join(all_outputs)

        self.chat_messages = self.chat_messages + [
            {
                "role": "assistant",
                "content": final_output,
            },
        ]

        firebase.firestore.collection(
            "chat_records",
        ).document(
            firebase.user_id,
        ).update(
            {
                "updated_at": FirestoreServerTimestamp,
                "num_chats": FirestoreIncrement(1),
                "num_characters_in": FirestoreIncrement(len(code)),
                "num_characters_out": FirestoreIncrement(len(final_output)),
            },
            firebase.firebase_user["idToken"],
        )

    def _gothub_use_model_image(self, code):
        self._gothub_print_markdown(f"**{got.get_model_name()}:**")

        response = got.get_client().images.generate(
            model=got.OPENAI_MODEL,
            prompt=code,
            **got.get_kwargs_for_chat_completions_create(),
        )

        for res in response:
            res_pretty = json.dumps(res, indent=4)
            self._gothub_print_markdown(f"```json\n{res_pretty}\n```")

        # firebase.firestore.collection(
        #     "chat_records",
        # ).document(
        #     firebase.user_id,
        # ).update(
        #     {
        #         "updated_at": FirestoreServerTimestamp,
        #         "num_chats": FirestoreIncrement(1),
        #         "num_characters_in": FirestoreIncrement(len(code)),
        #         "num_characters_out": FirestoreIncrement(len(final_output)),
        #     },
        #     firebase.firebase_user["idToken"],
        # )

    def _gothub_use_model(self, code):
        # ! This is pretty important
        got.OPENAI_MODEL = self.OPENAI_MODEL_TO_BE_SET

        match got.get_model_type():
            case "chat":
                self._gothub_use_model_chat(code)
            case "image":
                self._gothub_use_model_image(code)
            case _:
                raise NotImplementedError

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

            try:
                chat_record = (
                    firebase.firestore.collection(
                        "chat_records",
                    )
                    .document(
                        firebase.user_id,
                    )
                    .get(
                        token=firebase.firebase_user["idToken"],
                    )
                )

                if chat_record["num_chats"] >= 1000:
                    raise PleaseUpgradePlan(
                        "You have reached the usage limit for the free plan. "
                        "Please upgrade: "
                        "https://gothub-gpt.webflow.io/pricing"
                    )

            except requests.HTTPError as e:
                chat_record = (
                    firebase.firestore.collection(
                        "chat_records",
                    )
                    .document(
                        firebase.user_id,
                    )
                    .set(
                        {
                            "created_at": FirestoreServerTimestamp,
                            "updated_at": FirestoreServerTimestamp,
                            "num_chats": 0,
                            "num_characters_in": 0,
                            "num_characters_out": 0,
                        },
                        token=firebase.firebase_user["idToken"],
                    )
                )

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

                self._gothub_print_markdown(f"```json\n{who_am_i_pretty}\n```")

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

            with_model_regex_to_model_dict = {
                r"^\s*with\s+(?:gpt|gpt-)3.5(:|\s*$|\s+)": {
                    "model": "gpt-3.5-turbo",
                },
                r"^\s*with\s+(?:gpt|gpt-)4(:|\s*$|\s+)": {
                    "model": "gpt-4",
                },
                r"^\s*with\s+(?:mixtral)(:|\s*$|\s+)": {
                    "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
                },
                r"^\s*with\s+(?:llama|llama-)2(:|\s*$|\s+)": {
                    "model": "togethercomputer/llama-2-70b-chat",
                },
                r"^\s*with\s+(?:code-llama)(:|\s*$|\s+)": {
                    "model": "togethercomputer/CodeLlama-34b-Instruct",
                },
                r"^\s*with\s+(?:dall-e-)3(:|\s*$|\s+)": {
                    "model": "dall-e-3",
                },
            }
            for with_model_regex, model_dict in with_model_regex_to_model_dict.items():
                if with_model_match := re.match(with_model_regex, code):
                    return self._gothub_do_execute_with_model(
                        code,
                        with_model_match,
                        model_dict["model"],
                        silent=silent,
                        store_history=store_history,
                        user_expressions=user_expressions,
                        allow_stdin=allow_stdin,
                    )

            self._gothub_use_model(code)

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
