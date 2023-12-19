import json

import firebase
import requests
from google.cloud.firestore import SERVER_TIMESTAMP, Increment
from openai.types.images_response import ImagesResponse

# Firebase configuration
config = {
    "apiKey": "AIzaSyBX_nGfqOKq9t4G1200krLBsmm3XscJGsI",
    "authDomain": "gothub-dataengine.firebaseapp.com",
    "databaseURL": "https://gothub-dataengine-default-rtdb.firebaseio.com",
    "projectId": "gothub-dataengine",
    "storageBucket": "gothub-dataengine.appspot.com",
    "messagingSenderId": "752753357845",
    "appId": "1:752753357845:web:dbb61366b8df0c67440a1c",
    "measurementId": "G-TYR0BJFRTG",
}


# Instantiates a Firebase app
app = firebase.initialize_app(config)


auth = app.auth()
db = app.database()
firestore = app.firestore()


# From user
user_id = None
user_name = None
user_email = None
user_password = None
firebase_user: dict = {}


def get_user_records_else_create():
    chat_record = None
    image_record = None

    for _ in range(2):
        try:
            chat_record = (
                firestore.collection(
                    "chat_records",
                )
                .document(
                    user_id,
                )
                .get(
                    token=firebase_user["idToken"],
                )
            )
            break

        except requests.HTTPError as e:
            error_json = json.loads(e.strerror)
            if not (
                error_json["error"]["code"] == 404
                and error_json["error"]["status"] == "NOT_FOUND"
            ):
                raise e

            firestore.collection(
                "chat_records",
            ).document(
                user_id,
            ).set(
                {
                    "created_at": SERVER_TIMESTAMP,
                    "updated_at": SERVER_TIMESTAMP,
                    "num_chats": 0,
                    "num_characters_in": 0,
                    "num_characters_out": 0,
                },
                token=firebase_user["idToken"],
            )

    for _ in range(2):
        try:
            image_record = (
                firestore.collection(
                    "chat_records_for_images",
                )
                .document(
                    user_id,
                )
                .get(
                    token=firebase_user["idToken"],
                )
            )
            break

        except requests.HTTPError as e:
            error_json = json.loads(e.strerror)
            if not (
                error_json["error"]["code"] == 404
                and error_json["error"]["status"] == "NOT_FOUND"
            ):
                raise e

            firestore.collection(
                "chat_records_for_images",
            ).document(
                user_id,
            ).set(
                {
                    "created_at": SERVER_TIMESTAMP,
                    "updated_at": SERVER_TIMESTAMP,
                    "num_chats": 0,
                    "num_images": 0,
                    "num_characters_in": 0,
                    "num_characters_out": 0,
                },
                token=firebase_user["idToken"],
            )

    return {
        "chat_record": chat_record,
        "image_record": image_record,
    }


def update_chat_record(input: str, output: str):
    firestore.collection(
        "chat_records",
    ).document(
        user_id,
    ).update(
        {
            "updated_at": SERVER_TIMESTAMP,
            "num_chats": Increment(1),
            "num_characters_in": Increment(len(input)),
            "num_characters_out": Increment(len(output)),
        },
        firebase_user["idToken"],
    )


def update_image_record(input: str, response: ImagesResponse):
    total_input_len = len(input)
    total_output_len = sum(len(image.revised_prompt) for image in response.data)

    firestore.collection(
        "chat_records_for_images",
    ).document(
        user_id,
    ).update(
        {
            "updated_at": SERVER_TIMESTAMP,
            "num_chats": Increment(1),
            "num_images": Increment(len(response.data)),
            "num_characters_in": Increment(total_input_len),
            "num_characters_out": Increment(total_output_len),
        },
        firebase_user["idToken"],
    )
