"""Base Large Language Model (LLM) class."""

import logging
import re
from typing import Any, Mapping, Optional

from loguru import logger

from mtllm.types import OutputHint, TypeExplanation


httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)

SYSTEM_PROMPT = """
[System Prompt]
This is an operation you must perform and return the output values. Neither, the methodology, extra sentences nor the code are not needed.
Input/Type formatting: Explanation of the Input (variable_name) (type) = value
"""  # noqa E501


PROMPT_TEMPLATE = """
[Information]
{information}

[Context]
{context}

[Inputs Information]
{inputs_information}

[Output Information]
{output_information}

[Type Explanations]
{type_explanations}

[Action]
{action}
"""  # noqa E501

NORMAL_SUFFIX = """Generate and return the output result(s) only, adhering to the provided Type in the following format

[Output] <result>
"""  # noqa E501

REASON_SUFFIX = """
Reason and return the output result(s) only, adhering to the provided Type in the following format

[Reasoning] <Reason>
[Output] <Result>
"""

CHAIN_OF_THOUGHT_SUFFIX = """
Generate and return the output result(s) only, adhering to the provided Type in the following format. Perform the operation in a chain of thoughts.(Think Step by Step)

[Chain of Thoughts] <Chain of Thoughts>
[Output] <Result>
"""  # noqa E501

REACT_SUFFIX = """
"""  # noqa E501

MTLLM_OUTPUT_EXTRACT_PROMPT = """
[Output]
{model_output}

[Previous Result You Provided]
{previous_output}

[Desired Output Type]
{output_info}

[Type Explanations]
{output_type_info}

Above output is not in the desired Output Format/Type. Please provide the output in the desired type. Do not repeat the previously provided output.
Important: Do not provide the code or the methodology. Only provide the output in the desired format.
"""  # noqa E501

OUTPUT_CHECK_PROMPT = """
[Output]
{model_output}

[Desired Output Type]
{output_type}

[Type Explanations]
{output_type_info}

Check if the output is exactly in the desired Output Type. Important: Just say 'Yes' or 'No'.
"""  # noqa E501

OUTPUT_FIX_PROMPT = """
[Previous Output]
{model_output}

[Desired Output Type]
{output_type}

[Type Explanations]
{output_type_info}

[Error]
{error}

Above output is not in the desired Output Format/Type. Please provide the output in the desired type. Do not repeat the previously provided output.
Important: Do not provide the code or the methodology. Only provide the output in the desired format.
"""  # noqa E501


class BaseLLM:
    """Base Large Language Model (LLM) class."""

    MTLLM_SYSTEM_PROMPT: str = SYSTEM_PROMPT
    MTLLM_PROMPT: str = PROMPT_TEMPLATE
    MTLLM_METHOD_PROMPTS: dict[str, str] = {
        "Normal": NORMAL_SUFFIX,
        "Reason": REASON_SUFFIX,
        "Chain-of-Thoughts": CHAIN_OF_THOUGHT_SUFFIX,
        "ReAct": REACT_SUFFIX,
    }
    OUTPUT_EXTRACT_PROMPT: str = MTLLM_OUTPUT_EXTRACT_PROMPT
    OUTPUT_CHECK_PROMPT: str = OUTPUT_CHECK_PROMPT
    OUTPUT_FIX_PROMPT: str = OUTPUT_FIX_PROMPT

    def __init__(
        self, verbose: bool = False, max_tries: int = 10, type_check: bool = False
    ) -> None:
        """Initialize the Large Language Model (LLM) client."""
        self.verbose = verbose
        self.max_tries = max_tries
        self.type_check = type_check

    def __infer__(self, meaning_in: str | list[dict], **kwargs: dict) -> str:
        """Infer a response from the input meaning."""
        raise NotImplementedError

    def __call__(self, input_text: str | list[dict], **kwargs: dict) -> str:
        """Infer a response from the input text."""
        if self.verbose:
            logger.info(f"Meaning In\n{input_text}")
        return self.__infer__(input_text, **kwargs)

    def resolve_output(
        self,
        meaning_out: str,
        output_hint: OutputHint,
        output_type_explanations: list[TypeExplanation],
        _globals: dict,
        _locals: Mapping,
    ) -> str:
        """Resolve the output string to return the reasoning and output."""
        if self.verbose:
            logger.info(f"Meaning Out\n{meaning_out}")
        output_match = re.search(r"\[Output\](.*)", meaning_out, re.DOTALL)
        if not output_match:
            output = self._extract_output(
                meaning_out,
                output_hint,
                output_type_explanations,
                self.max_tries,
            )
        else:
            output = output_match.group(1).strip()
        if self.type_check:
            is_in_desired_format = self._check_output(
                output, output_hint.type, output_type_explanations
            )
            if not is_in_desired_format:
                output = self._extract_output(
                    meaning_out,
                    output_hint,
                    output_type_explanations,
                    self.max_tries,
                    output,
                )

        return self.to_object(
            output, output_hint, output_type_explanations, _globals, _locals
        )

    def _check_output(
        self,
        output: str,
        output_type: str,
        output_type_explanations: list[TypeExplanation],
    ) -> bool:
        """Check if the output is in the desired format."""
        output_check_prompt = self.OUTPUT_CHECK_PROMPT.format(
            model_output=output,
            output_type=output_type,
            output_type_info="\n".join(
                [str(info) for info in output_type_explanations]
            ),
        )
        llm_output = self.__infer__(output_check_prompt)
        return "yes" in llm_output.lower()

    def _extract_output(
        self,
        meaning_out: str,
        output_hint: OutputHint,
        output_type_explanations: list[TypeExplanation],
        max_tries: int,
        previous_output: str = "None",
    ) -> str:
        """Extract the output from the meaning out string."""
        if max_tries == 0:
            logger.error("Failed to extract output. Max tries reached.")
            raise ValueError(
                "Failed to extract output. Try Changing the Semstrings, provide examples or change the method."
            )

        if self.verbose:
            if max_tries < self.max_tries:
                logger.info(
                    f"Failed to extract output. Trying to extract output again. Max tries left: {max_tries}"
                )
            else:
                logger.info("Extracting output from the meaning out string.")

        output_extract_prompt = self.OUTPUT_EXTRACT_PROMPT.format(
            model_output=meaning_out,
            previous_output=previous_output,
            output_info=str(output_hint),
            output_type_info="\n".join(
                [str(info) for info in output_type_explanations]
            ),
        )
        llm_output = self.__infer__(output_extract_prompt)
        is_in_desired_format = self._check_output(
            llm_output, output_hint.type, output_type_explanations
        )
        if self.verbose:
            logger.info(
                f"Extracted Output: {llm_output}. Is in Desired Format: {is_in_desired_format}"
            )
        if is_in_desired_format:
            return llm_output
        return self._extract_output(
            meaning_out,
            output_hint,
            output_type_explanations,
            max_tries - 1,
            llm_output,
        )

    def to_object(
        self,
        output: str,
        output_hint: OutputHint,
        output_type_explanations: list[TypeExplanation],
        _globals: dict,
        _locals: Mapping,
        error: Optional[Exception] = None,
        num_retries: int = 0,
    ) -> Any:  # noqa: ANN401
        """Convert the output string to an object."""
        if num_retries >= self.max_tries:
            raise ValueError("Failed to convert output to object. Max tries reached.")
        if output_hint.type == "str":
            return output
        if error:
            fixed_output = self._fix_output(
                output, output_hint, output_type_explanations, error
            )
            return self.to_object(
                fixed_output,
                output_hint,
                output_type_explanations,
                _globals,
                _locals,
                num_retries=num_retries + 1,
            )

        try:
            return eval(output, _globals, _locals)
        except Exception as e:
            return self.to_object(
                output,
                output_hint,
                output_type_explanations,
                _globals,
                _locals,
                error=e,
                num_retries=num_retries + 1,
            )

    def _fix_output(
        self,
        output: str,
        output_hint: OutputHint,
        output_type_explanations: list[TypeExplanation],
        error: Exception,
    ) -> str:
        """Fix the output string."""
        if self.verbose:
            logger.info(f"Error: {error}, Fixing the output.")
        output_fix_prompt = self.OUTPUT_FIX_PROMPT.format(
            model_output=output,
            output_type=output_hint.type,
            output_type_info="\n".join(
                [str(info) for info in output_type_explanations]
            ),
            error=error,
        )
        return self.__infer__(output_fix_prompt)
