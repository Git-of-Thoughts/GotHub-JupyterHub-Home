import requests

from gothub_kernel_launcher.kernels.configs import server_sub_url
from gothub_kernel_launcher.kernels.utils import firebase


def super_king_debug(self):
    user_folder = f"/chat/{self.user_id}"

    def callback(event):
        self._ChatGptKernel__print(str(event))

    child_key = firebase.db.child(
        user_folder,
    ).push(
        "super king debug",
        self.firebase_user["idToken"],
    )

    firebase.db.child(
        f"{user_folder}/{child_key['name']}",
    ).stream(
        callback,
        self.firebase_user["idToken"],
    )

    # response = requests.post(
    #         server_sub_url("chat"),
    #         json={
    #             "event": event,
    #             "messages": "super king debug",
    #         },
    #     )
    #     response.raise_for_status()
    #     response_json = response.json()
