import openai

from .utils import bold

OPENAI_MODEL = "gpt-4"


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

    if model is None:
        model = OPENAI_MODEL

    response = openai.ChatCompletion.create(
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
            [
                choice["delta"]["content"] if "content" in choice["delta"] else ""
                for choice in res["choices"]
            ]
        )

        all_outputs.append(output)

        print(output, end="")
    print("\n")

    return "".join(all_outputs)


def ask(
    question: str = "",
    *,
    system_prompt: str = "",
    prompt: str = "",
    model: str | None = None,
) -> str:
    try:
        result = _ask(
            question=question,
            system_prompt=system_prompt,
            prompt=prompt,
            model=model,
        )

    except openai.error.AuthenticationError as e:
        msg = (
            "Please set OPENAI_API_KEY in $HOME/__keys__.yaml, and restart the kernel."
        )
        raise openai.error.AuthenticationError(msg) from e

    return result
