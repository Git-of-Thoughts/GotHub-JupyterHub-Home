import sys


def main():
    """
    Copied from
    https://github.com/ipython/ipykernel/blob/e9ddcf50a30b59d63f585ffa9ffffd368095a54a/ipykernel_launcher.py#L9
    """

    # Remove the CWD from sys.path while we load stuff.
    # This is added back by InteractiveShellApp.init_path()
    if sys.path[0] == "":
        del sys.path[0]

    from ipykernel import kernelapp as app

    app.launch_new_instance()
