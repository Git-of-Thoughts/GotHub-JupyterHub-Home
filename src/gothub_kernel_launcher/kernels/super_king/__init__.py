import requests

from gothub_kernel_launcher.kernels.configs import server_sub_url
from gothub_kernel_launcher.kernels.utils import firebase


def super_king_debug(self):
    response = requests.post(
        server_sub_url("chat"),
        json={
            "user_id": self.user_id,
            "messages": "super king debug",
        },
    )
    response.raise_for_status()
    response_json = response.json()

    ref_path = response_json["ref_path"]

    def callback(event):
        self._ChatGptKernel__print(str(event))

    firebase.db.child(ref_path).stream(callback, is_async=False)
