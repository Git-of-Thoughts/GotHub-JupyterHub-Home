"""
Copied from
https://github.com/ipython/ipykernel/blob/e9ddcf50a30b59d63f585ffa9ffffd368095a54a/ipykernel_launcher.py#L9
and
https://jupyter-client.readthedocs.io/en/latest/wrapperkernels.html
"""


import sys

import got
from gothub_kernel_launcher.kernels.chatgpt_kernel import ChatGptKernel
from ipykernel.kernelapp import IPKernelApp

if __name__ == "__main__":
    # Remove the CWD from sys.path while we load stuff.
    # This is added back by InteractiveShellApp.init_path()
    if sys.path[0] == "":
        del sys.path[0]

    got.DEFAULT_OPENAI_MODEL = "dall-e-3"

    IPKernelApp.launch_instance(
        kernel_class=ChatGptKernel,
    )
