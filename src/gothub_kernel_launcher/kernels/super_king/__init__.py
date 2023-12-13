from typing import TYPE_CHECKING

import requests

from gothub_kernel_launcher.kernels.configs import SERVER_TIMEOUT, server_sub_url
from gothub_kernel_launcher.kernels.utils import firebase

if TYPE_CHECKING:
    from gothub_kernel_launcher.kernels.chatgpt_kernel import ChatGptKernel


def super_king_debug(self: "ChatGptKernel"):
    stream_content = {
        "metadata": {},
        "data": {
            "text/html": '<iframe src="https://wikipedia.com/"></iframe>',
        },
    }
    self.send_response(
        self.iopub_socket,
        "display_data",
        stream_content,
    )


def chat_through_firebase_realtime_db(self: "ChatGptKernel"):
    user_folder = f"/chat/{self.user_id}"

    child_key = firebase.db.child(
        user_folder,
    ).push(
        "super king debug",
        self.firebase_user["idToken"],
    )

    ref_path = f"{user_folder}/{child_key['name']}"
    self._ChatGptKernel__print(ref_path)

    # TODO chat_request

    def callback(event):
        self._ChatGptKernel__print(str(event))

    firebase.db.child(
        ref_path,
    ).stream(
        callback,
        self.firebase_user["idToken"],
        is_async=False,
    )
