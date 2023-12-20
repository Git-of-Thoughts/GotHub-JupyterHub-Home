import replicate
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


openai_client: OpenAI = None
together_client: OpenAI = None
replicate_client: replicate.Client = None


def get_client():
    match OPENAI_MODEL:
        case "gpt-4":
            return openai_client
        case "gpt-3.5-turbo":
            return openai_client
        case "dall-e-3":
            return openai_client
        case "mistralai/Mixtral-8x7B-Instruct-v0.1":
            return together_client
        case "togethercomputer/llama-2-70b-chat":
            return together_client
        case "togethercomputer/CodeLlama-34b-Instruct":
            return together_client
        case (
            "stability-ai/sdxl"
            ":39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
        ):
            return replicate_client
        case _:
            raise ValueError(f"Unknown model: {OPENAI_MODEL}")


def get_model_name() -> str:
    match OPENAI_MODEL:
        case "gpt-4":
            return "ChatGPT 4"
        case "gpt-3.5-turbo":
            return "ChatGPT 3.5"
        case "dall-e-3":
            return "DALL·E 3"
        case "mistralai/Mixtral-8x7B-Instruct-v0.1":
            return "Mixtral 8x7B"
        case "togethercomputer/llama-2-70b-chat":
            return "Llama 2 (70B)"
        case "togethercomputer/CodeLlama-34b-Instruct":
            return "Code Llama (34B)"
        case (
            "stability-ai/sdxl"
            ":39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
        ):
            return "Stable Diffusion XL"
        case _:
            raise ValueError(f"Unknown model: {OPENAI_MODEL}")


def get_model_type() -> str:
    match OPENAI_MODEL:
        case "gpt-4":
            return "chat"
        case "gpt-3.5-turbo":
            return "chat"
        case "dall-e-3":
            return "image"
        case "mistralai/Mixtral-8x7B-Instruct-v0.1":
            return "chat"
        case "togethercomputer/llama-2-70b-chat":
            return "chat"
        case "togethercomputer/CodeLlama-34b-Instruct":
            return "chat"
        case (
            "stability-ai/sdxl"
            ":39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
        ):
            return "image"
        case _:
            raise ValueError(f"Unknown model: {OPENAI_MODEL}")


def get_kwargs_for_chat_completions_create() -> dict:
    match OPENAI_MODEL:
        case "gpt-4":
            return {}
        case "gpt-3.5-turbo":
            return {}
        case "dall-e-3":
            return {}
        case "mistralai/Mixtral-8x7B-Instruct-v0.1":
            return {
                "stop": ["</s>"],
            }
        case "togethercomputer/llama-2-70b-chat":
            return {
                "stop": ["</s>"],
            }
        case "togethercomputer/CodeLlama-34b-Instruct":
            return {
                "max_tokens": 16384 // 2,
                "stop": ["</s>"],
            }
        case _:
            raise ValueError(f"Unknown model: {OPENAI_MODEL}")


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

    response = get_client().chat.completions.create(
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
        **get_kwargs_for_chat_completions_create(),
    )

    print(bold(f"{get_model_name()}:"))

    all_outputs = []
    for res in response:
        output = "".join(
            [choice.delta.content or "" for choice in res.choices],
        )

        all_outputs.append(output)

        print(output, end="", flush=True)
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
