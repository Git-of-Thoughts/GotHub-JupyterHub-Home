SERVER_URL = "https://gothub-flask.vercel.app"


def server_sub_url(sub_url):
    return f"{SERVER_URL}/{sub_url}"


SERVER_LOGIN_NUM_ATTEMPTS = 3
SERVER_LOGIN_TIMEOUT = 5
