import requests

from gothub_kernel_launcher.kernels.configs import server_sub_url
from gothub_kernel_launcher.kernels.utils import firebase


def super_king_debug(self):
    self.super_king_debug_res = (
        self.super_king_debug_res if self.super_king_debug_res else None
    )
    self.send_response(
        self.iopub_socket,
        "stream",
        {
            "name": "stdout",
            "text": str(self.super_king_debug_res),
        },
    )

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
        self.super_king_debug_res = event

    firebase.db.child(ref_path).stream(callback)
