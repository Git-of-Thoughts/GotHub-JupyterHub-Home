import json
import os
import re
import sys
from pathlib import Path

import got
import replicate
import requests
from ipykernel.ipkernel import IPythonKernel
from IPython import get_ipython
from IPython.display import Markdown, clear_output, display
from openai import OpenAI

from .configs import (
    SERVER_LOGIN_NUM_ATTEMPTS,
    SERVER_TIMEOUT,
    server_sub_url,
)
from .errors import PleaseUpgradePlan
from .super_king import super_king_debug
from .utils import firebase
from .utils.firebase import (
    get_user_records_else_create,
    update_chat_record,
    update_image_record,
)

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
        got.replicate_client = replicate.Client(
            api_token=my_firebase_password_json["REPLICATE_API_TOKEN"],
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
        # ! You can't do this (probably due to async when running as code)
        # got.OPENAI_MODEL = self.OPENAI_MODEL_TO_BE_SET

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
        # get_ipython().set_next_input(final_output)

        self.chat_messages = self.chat_messages + [
            {
                "role": "assistant",
                "content": final_output,
            },
        ]

        update_chat_record(code, final_output)

    def _gothub_use_model_image(self, code):
        self._gothub_print_markdown(f"**{got.get_model_name()}:**")
        self._gothub_print_markdown("Generating image...")

        response = got.get_client().images.generate(
            model=got.OPENAI_MODEL,
            prompt=code,
            **got.get_kwargs_for_chat_completions_create(),
        )

        for image in response.data:
            url = image.url
            description = image.revised_prompt
            self._gothub_print_markdown(f"![{description}]({url})")
            self._gothub_print_markdown(f"> {description}")

        update_image_record(
            code,
            num_images=len(response.data),
            total_output_len=sum(
                [len(image.revised_prompt) for image in response.data],
            ),
        )

    def _gothub_use_model_r8_image(self, code):
        self._gothub_print_markdown(f"**{got.get_model_name()}:**")
        self._gothub_print_markdown("Generating image...")

        response = got.get_client().run(
            got.OPENAI_MODEL,
            input={
                "prompt": code,
            },
            **got.get_kwargs_for_chat_completions_create(),
        )

        for image in response:
            url = image
            description = code
            self._gothub_print_markdown(f"![{description}]({url})")
            self._gothub_print_markdown(f"> {description}")

        update_image_record(
            code,
            num_images=len(response),
            total_output_len=sum(
                [len(code) for image in response],
            ),
        )

    def _gothub_do_execute(
        self,
        code: str,
        *,
        as_code: bool,
        silent,
        store_history,
        user_expressions,
        allow_stdin,
    ):
        # ! This is pretty important
        got.OPENAI_MODEL = self.OPENAI_MODEL_TO_BE_SET

        if as_code:
            return super().do_execute(
                code,
                silent,
                store_history,
                user_expressions,
                allow_stdin,
            )

        match got.get_model_type():
            case "chat":
                self._gothub_use_model_chat(code)
            case "image":
                self._gothub_use_model_image(code)
            case "r8_image":
                self._gothub_use_model_r8_image(code)
            case _:
                raise NotImplementedError

        return super().do_execute(
            "None",
            silent,
            store_history,
            user_expressions,
            allow_stdin,
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

            user_records = get_user_records_else_create()
            if user_records["chat_record"]["num_chats"] >= 1000:
                raise PleaseUpgradePlan(
                    "You have reached the usage limit for the free plan. "
                    "Please upgrade: "
                    "https://gothub-gpt.webflow.io/pricing"
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
                return self._gothub_do_execute(
                    code,
                    as_code=True,
                    silent=silent,
                    store_history=store_history,
                    user_expressions=user_expressions,
                    allow_stdin=allow_stdin,
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
                r"^\s*with\s+(?:sdxl)(:|\s*$|\s+)": {
                    "model": (
                        "stability-ai/sdxl"
                        ":39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
                    ),
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

            return self._gothub_do_execute(
                code,
                as_code=False,
                silent=silent,
                store_history=store_history,
                user_expressions=user_expressions,
                allow_stdin=allow_stdin,
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
            # ! But somehow it's not increasing unless "as code" is used
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }
