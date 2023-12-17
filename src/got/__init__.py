from google.cloud.firestore import (
    SERVER_TIMESTAMP as FirestoreServerTimestamp,
)
from google.cloud.firestore import (
    Increment as FirestoreIncrement,
)
from gothub_kernel_launcher.kernels.utils import firebase
from openai import OpenAI

from .utils import bold

DEFAULT_OPENAI_MODEL = "gpt-4"


OPENAI_MODEL = DEFAULT_OPENAI_MODEL


client: OpenAI = None


def _ask(
    question: str = "",
    *,
    system_prompt: str = "",
    prompt: str = "",
    model: str | None = None,
) -> str:
    if not any([question, system_prompt, prompt]):
        raise ValueError(
            "At least one of question, system_prompt, prompt must be provided"
        )

    if question and prompt:
        raise ValueError("Only one of question or prompt can be provided")

    user_prompt = question or prompt
    model = model or OPENAI_MODEL

    response = client.chat.completions.create(
        model=model,
        messages=[  # TODO use system messages
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        stream=True,
    )

    print(bold(f"ChatGPT {model}:"))

    all_outputs = []
    for res in response:
        output = "".join(
            [choice.delta.content or "" for choice in res.choices],
        )

        all_outputs.append(output)

        print(output, end="")
    print("\n")

    final_output = "".join(all_outputs)

    firebase.firestore.collection(
        "chat_records",
    ).document(
        firebase.user_id,
    ).update(
        {
            "updated_at": FirestoreServerTimestamp,
            "num_chats": FirestoreIncrement(1),
            "num_characters_in": FirestoreIncrement(len(user_prompt)),
            "num_characters_out": FirestoreIncrement(len(final_output)),
        },
        firebase.firebase_user["idToken"],
    )

    return final_output


def ask(
    question: str = "",
    *,
    system_prompt: str = "",
    prompt: str = "",
    model: str | None = None,
) -> str:
    final_output = _ask(
        question=question,
        system_prompt=system_prompt,
        prompt=prompt,
        model=model,
    )

    return final_output
