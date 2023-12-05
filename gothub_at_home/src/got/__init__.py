import openai

OPENAI_MODEL = "gpt-4"


def ask(
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

    all_outputs = []
    for res in response:
        output = "".join(
            [
                choice["delta"]["content"] if "content" in choice["delta"] else ""
                for choice in res["choices"]
            ]
        )

        print(output, end="")

        all_outputs.append(output)

    return "".join(all_outputs)
