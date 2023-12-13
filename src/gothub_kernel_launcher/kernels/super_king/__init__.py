import requests

from gothub_kernel_launcher.kernels.configs import SERVER_TIMEOUT, server_sub_url
from gothub_kernel_launcher.kernels.utils import firebase


def super_king_debug(self):
    user_folder = f"/chat/{self.user_id}"

    child_key = firebase.db.child(
        user_folder,
    ).push(
        "super king debug",
        self.firebase_user["idToken"],
    )

    ref_path = f"{user_folder}/{child_key['name']}"

    chat_request = requests.post(
        server_sub_url("chat"),
        json={
            "ref_path": ref_path,
            "messages": "hello there",
        },
        timeout=SERVER_TIMEOUT,
    )
    chat_request.raise_for_status()

    def callback(event):
        self._ChatGptKernel__print(str(event))

    firebase.db.child(
        ref_path,
    ).stream(
        callback,
        self.firebase_user["idToken"],
        is_async=False,
    )
