import requests

from gothub_kernel_launcher.kernels.configs import server_sub_url
from gothub_kernel_launcher.kernels.utils import firebase


def super_king_debug(self):
    user_folder = f"/chat/{self.user_id}"
    # response = requests.post(
    #     server_sub_url("chat"),
    #     json={
    #         "user_id": self.user_id,
    #         "messages": "super king debug",
    #     },
    # )
    # response.raise_for_status()
    # response_json = response.json()

    # ref_path = response_json["ref_path"]

    def callback(event):
        self._ChatGptKernel__print(str(event))

    child_key = firebase.db.child(user_folder).push(
        "super king debug",
        self.firebase_user["idToken"],
    )
    self._ChatGptKernel__print(child_key)

    firebase.db.child(f"{user_folder}/{child_key['name']}").stream(
        callback,
        self.firebase_user["idToken"],
        is_async=False,
    )
