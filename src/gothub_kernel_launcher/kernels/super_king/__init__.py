import requests

from gothub_kernel_launcher.kernels.configs import server_sub_url


def super_king_debug(self):
    requests.post(
        server_sub_url("chat"),
        json={
            "user_id": self.user_id,
            "message": "super king debug",
        },
    )
