"""Claude tool-calling loop."""

import logging

import anthropic

from .tools import Toolbox

logger = logging.getLogger(__name__)

REFUSAL_MESSAGE = "Lo siento, no puedo ayudarte con eso. ¿Quieres que te recomiende algo más?"
TRUNCATED_MESSAGE = "Mi respuesta quedó incompleta. ¿Puedes reformular tu pregunta?"
GAVE_UP_MESSAGE = "No logré completar la consulta. ¿Puedes intentarlo de nuevo?"


class AssistantError(Exception):
    """The model could not be reached; ``str(exc)`` is safe to show to the user."""


class ChatAssistant:
    def __init__(
        self,
        client: anthropic.Anthropic,
        toolbox: Toolbox,
        *,
        model: str,
        effort: str = "low",
        max_tokens: int = 4096,
        max_iterations: int = 5,
    ):
        self._client = client
        self._toolbox = toolbox
        self._model = model
        self._effort = effort
        self._max_tokens = max_tokens
        self._max_iterations = max_iterations

    def reply(self, system: str, history: list[dict]) -> str:
        """Run the model until it stops calling tools and return its final text."""
        messages = list(history)
        for _ in range(self._max_iterations):
            response = self._create(system, messages)

            if response.stop_reason == "refusal":
                return REFUSAL_MESSAGE
            if response.stop_reason == "max_tokens":
                return _text(response) or TRUNCATED_MESSAGE
            if response.stop_reason != "tool_use":
                return _text(response)

            # Replay the assistant turn unchanged (tool_use and thinking blocks included),
            # then answer every tool call in a single user message.
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": self._run_tools(response)})
        return GAVE_UP_MESSAGE

    def _create(self, system: str, messages: list[dict]):
        try:
            return self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                tools=self._toolbox.definitions,
                messages=messages,
                output_config={"effort": self._effort},
            )
        except anthropic.RateLimitError as exc:
            logger.warning("Anthropic rate limit: %s", exc)
            raise AssistantError(
                "Estoy recibiendo muchas consultas. Intenta de nuevo en un momento."
            ) from exc
        except anthropic.APIConnectionError as exc:
            logger.warning("Anthropic connection error: %s", exc)
            raise AssistantError("No pude conectarme con el asistente. Intenta de nuevo.") from exc
        except anthropic.APIStatusError as exc:
            logger.error("Anthropic API error %s (request %s)", exc.status_code, exc.request_id)
            raise AssistantError("El asistente no está disponible por ahora.") from exc

    def _run_tools(self, response) -> list[dict]:
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                content, is_error = self._toolbox.run(block.name, block.input), False
            except Exception:  # a failing tool must not take the whole request down
                logger.exception("Tool %s failed", block.name)
                content, is_error = "La herramienta falló. Responde sin esa información.", True
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                }
            )
        return results


def _text(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text").strip()
