from ipykernel.kernelbase import Kernel


class EchoKernel(Kernel):
    """
    Copied from
    https://ipython.readthedocs.io/en/3.x/development/wrapperkernels.html
    and
    https://jupyter-client.readthedocs.io/en/latest/wrapperkernels.html
    """

    implementation = "Echo"
    implementation_version = "1.0"
    language = "no-op"
    language_version = "0.1"
    language_info = {
        "name": "Any text",
        "mimetype": "text/plain",
        "file_extension": ".txt",
    }
    banner = "Echo kernel - as useful as a parrot"

    def do_execute(
        self,
        code,
        silent,
        store_history=True,
        user_expressions=None,
        allow_stdin=False,
    ):
        if not silent:
            stream_content = {
                "name": "stdout",
                "text": code,
            }
            self.send_response(
                self.iopub_socket,
                "stream",
                stream_content,
            )

        return {
            "status": "ok",
            # The base class increments the execution count
            "execution_count": self.execution_count,
            "payload": [],
            "user_expressions": {},
        }
