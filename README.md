*This project has been created as part of the 42 curriculum by kamurai.*

# call me maybe

## Description

This program translates natural-language prompts into function calls.
For each prompt, it outputs JSON that contains the name of the function to call and its arguments.

- **Input 1**: a JSON file of prompts (`data/input/function_calling_tests.json`)

  ```json
  [
    {
      "prompt": "What is the sum of 2 and 3?"
    },
    {
      "prompt": "Greet shrek"
    },
    ...
  ]
  ```

- **Input 2**: a JSON file of function definitions (`data/input/functions_definition.json`)

  ```json
  [
    {
      "name": "fn_add_numbers",
      "description": "Add two numbers together and return their sum.",
      "parameters": {
        "a": {
          "type": "number"
        },
        "b": {
          "type": "number"
        }
      },
      "returns": {
        "type": "number"
      }
    },
    ...
  ]
  ```

- **Processing**: for each prompt in Input 1, the program uses the LLM (Qwen/Qwen3-0.6B) to choose a function from Input 2.
  It then generates the arguments to pass, using constrained decoding.
- **Output**: a JSON array of objects, each with `prompt`, `name` and `parameters` (`data/output/function_calling_results.json`)

  ```json
  [
    {
      "prompt": "What is the sum of 2 and 3?",
      "name": "fn_add_numbers",
      "parameters": {
        "a": 2.0,
        "b": 3.0
      }
    },
    {
      "prompt": "Greet shrek",
      "name": "fn_greet",
      "parameters": {
        "name": "shrek"
      }
    },
    ...
  ]
  ```

## Instructions

### Requirements

- Python 3.10 or later
- [uv](https://docs.astral.sh/uv/)

### Makefile rules

| Rule | Description |
| --- | --- |
| `make` / `make usage` | Show the list of rules |
| `make install` | Install the dependencies (`uv sync`) |
| `make run` | Run the program (`uv run python -m src`) |
| `make debug` | Run the program with `pdb` |
| `make clean` | Remove `__pycache__`, `.mypy_cache` and `.pytest_cache` |
| `make lint` | Run `flake8` and `mypy .` with the required flags |
| `make lint-strict` | Run `flake8` and `mypy . --strict` |

`make install` installs numpy, pydantic, flake8, mypy and the bundled `llm_sdk` package (from `./llm_sdk`).
The model (Qwen/Qwen3-0.6B) is downloaded automatically on the first run.

## Example usage

Run with the default paths:

    uv run python -m src

Run with explicit paths:

    uv run python -m src \
        --functions_definition data/input/functions_definition.json \
        --input data/input/function_calling_tests.json \
        --output data/output/function_calls.json

Example output:

    [
      {
        "prompt": "What is the sum of 2 and 3?",
        "name": "fn_add_numbers",
        "parameters": {"a": 2.0, "b": 3.0}
      }
    ]

If an input file is missing or is not valid JSON, the program prints an error message to standard error.
It then exits with status 1 and does not show a traceback.

## Algorithm explanation

### 1. Function selection (`FunctionSelector.select()`)

1. Build the model input from the prompt (see "Prompt design" for its content).
2. For each function name in Input 2, compute how likely the LLM is to produce that name as the continuation of the input.
   - A function name is made of several tokens (sub-word pieces).
     For each token, the program takes the probability that it follows the preceding text, computed with softmax over the logits.
     It adds up the logs of these probabilities (log-probabilities) to get a score.
   - The score is the log of the probability that the whole function name comes next.
   - The program uses `log_z = max + log(sum(exp(x - max)))` (log-sum-exp) to avoid underflow.
3. Select the function with the highest score.
   The LLM only ranks the candidates and never writes the name freely, so the output always names a function that exists in Input 2.

### 2. Argument generation (`ConstrainedDecoder.generate_arguments()`)

1. For each argument of the selected function, build the model input (see "Prompt design" for its content).
2. Generate the value one token at a time:
   1. Get the logits for every token from `get_logits_from_input_ids`.
   2. Sort the token IDs by logit, highest first.
   3. If the top token does not fit the argument type, treat the value as finished and stop.
   4. Otherwise, select the highest-ranked token for which (value so far + token) is still a valid prefix of the type.
      Every token that would break the type is skipped, which is the same as setting its logit to negative infinity.
   5. Stop also when no token fits, or after `MAX_NEW_TOKENS` (50) tokens.
3. Convert the generated text to the argument type.

What each type allows:

| Type | Allowed (prefix) | Converted to |
| --- | --- | --- |
| `number` | digits, a leading `-`, at most one `.` | `float` |
| `integer` | digits, a leading `-` | `int` |
| `boolean` | a prefix of `true` or `false` | `bool` |
| `string` | any text without `"` or a newline | `str` |

### 3. Token-to-text mapping (`Vocab.to_text()`)

- The vocabulary file returned by `get_path_to_vocab_file()` maps token strings to IDs.
  The token strings use the byte-level BPE notation: `Ġ` stands for a space and `Ċ` for a newline.
- `to_text(token_id)` looks up the token and maps each character back to its original byte.
  It then decodes the bytes as UTF-8.
  An incomplete multi-byte sequence becomes `�`.
- IDs that are not in the vocabulary (special tokens, unused IDs) return an empty string.
  These IDs are never selected as part of a value.

### 4. Output

The output is written with `json.dump`, so the file is always valid JSON.
Each value is converted to the type given in the function definition, so the output also matches the schema.

## Prompt design

The LLM only predicts which token is likely to come next after the given text.
The hints in that text therefore have a large effect on how often the function and the arguments are correct.
The program builds the text with three rules:

1. **Include the list of available functions**, so the model can match the prompt to a function description.
2. **Include one example**, to show the answer format `Call: <name>(<arg>=<value>, ...)`.
3. **Use the same format for function selection and argument generation**: the text for an argument continues the text used for function selection.

### Common preface

The program builds the list of available functions from the function definitions file (`FunctionSelector._make_text_header()`).
One fixed example follows the list.

```text
Available functions:
- fn_add_numbers(a: number, b: number): Add two numbers together and return their sum.
- fn_greet(name: string): Generate a greeting message for a person by name.
- fn_reverse_string(s: string): Reverse a string and return the reversed result.
- fn_get_square_root(a: number): Calculate the square root of a number.
- fn_substitute_string_with_regex(source_string: string, regex: string, replacement: string): Replace all occurrences matching a regex pattern in a string.

Example:
Question: What is the sum of 10 and 20?
Call: fn_add_numbers(a=10, b=20)
```

- Without the list, the model sees only the names of the functions.
  For example, it cannot match a prompt such as "Replace all ..." to `fn_substitute_string_with_regex`.
- The example shows the answer format.
  It uses a function with two arguments, and values (10 and 20) that differ from the test prompts.
  Because the example is an addition, it may make `fn_add_numbers` more likely to be selected.

### Text for function selection (`FunctionSelector.select()`)

The prompt follows the common preface.

```text
(common preface)

Question: What is the sum of 2 and 3?
Call:
```

- Each candidate function name is placed after this text, and its score is computed.
- The text ends with `Call:`, and the space goes in front of the function name (`" fn_add_numbers"`).
  The tokenizer joins a space to the next word (`" fn"` is one token),
  so the tokens are split in the same way as in the example `Call: fn_add_numbers`.
- With the list, once the first few tokens of a name are chosen, the remaining tokens follow almost certainly.
  As a result, a long name with many tokens does not get a much lower score.

### Text for argument generation (`ConstrainedDecoder.generate_arguments()`)

The program builds one text for each argument, and ends it where the value should start.

```text
Question: What is the sum of 2 and 3?
Call: fn_add_numbers(a=
```

```text
Question: What is the sum of 2 and 3?
Call: fn_add_numbers(a=2, b=
```

```text
Question: Greet shrek
Call: fn_greet(name="
```

- **Include the arguments already generated**: when generating `b`, the text includes `a=2, ` (`arg_texts`).
  Without it, the texts for `a` and `b` are almost identical, so the model repeats the value of `a`.
- **End with `"` for a string**: the start of the value is clear, and the model writes the value inside the quotes.
  The type check rejects the closing `"`, so the generation stops there.

### Effect of the prompt changes

| Change | Function selection | Arguments |
| --- | --- | --- |
| Before (prompt + `Function name: `) | 8 / 11 | 2 / 11 |
| New text for function selection | 11 / 11 | 2 / 11 |
| New text for argument generation as well | TODO | TODO |

### Problems the prompt cannot solve

- A `]` in a regex is lost: the model writes `]"` as one token, and the whole token is rejected because it contains `"`.
- `\d` becomes `\\d`: inside `"`, the model escapes `\` as `\\`.

These problems are handled by the token selection and the value conversion, not by the prompt.

## Design decisions

- **Choosing the function by score instead of free generation**: the LLM ranks only the existing function names, so it can never invent a function.
  No keyword matching or other heuristics are used.
- **Generating only the values**: the program writes the keys and the JSON structure itself, so the model generates only the argument values.
  This removes structural errors and reduces the number of model calls.
- **Using `vocab.json` instead of `decode`**: the program checks the type of every candidate token.
  Its own token-to-text table keeps the program independent of the optional `decode` method.
- **Pydantic models**: input models (`FunctionDefinition`, `Prompt`, `ParameterSpec`) ignore unknown keys (`extra="ignore"`), and the output model `FunctionCall` rejects them (`extra="forbid"`).
  Supported argument and return types are `number`, `integer`, `string` and `boolean`; any other type is reported as an `InputFileError`.
- **Error handling**: errors are grouped into project-specific exceptions (`InputFileError`, `OutputFileError`, `ModelError`, `DecodingError`), all based on `CallMeMaybeError`.
  `main()` catches these and any unexpected exception, prints a clear message and returns exit status 1.
- **File I/O**: `io_utils.py` reads and writes JSON with the standard `json` module.
  Files are always opened with `with open(...)`, so they are closed automatically.
  `json.load(f)` converts a JSON file into Python data (`dict` / `list`); it is used in `load_function_definitions()` and `load_prompts()`.
  `json.dump(data, f)` writes Python data to a file as JSON; it is used in `save_function_calls()`.
  A missing input file (`FileNotFoundError`) and invalid JSON (`json.JSONDecodeError`) are both raised as `InputFileError`.

## Performance analysis

> TODO: fill in after running `make run` on the provided test set.

| Metric | Result |
| --- | --- |
| Function selection accuracy | TODO (correct / total) |
| Argument accuracy | TODO |
| Valid JSON | TODO |
| Total time for all prompts | TODO (target: under 5 minutes) |
| Machine | TODO (CPU / GPU, RAM) |

## Challenges faced

- **Knowing when a value is finished**: picking the best valid token at every step means the model never stops by itself.
  The fix was to stop as soon as the model's top token no longer fits the type, which treats it as "the model wants to end the value".
- **Byte-level BPE tokens**: the token strings in `vocab.json` are not plain text (`Ġis` means `" is"`).
  The fix was to rebuild the byte mapping and decode the bytes as UTF-8.
- **Partial numbers**: a check that only looked at allowed characters accepted values such as `1.2.3` and `1-2`, which crashed the conversion.
  Now `-` is allowed only as the first character and `.` at most once.
  The conversion also falls back to `0` / `0.0` if a value is unfinished.

## Testing strategy

- `_is_allowed` was tested with valid and invalid partial values (for example `1.2.3`, `1-2`, `--5`, `-1.5`, `-`).
- `_convert` was tested with unfinished values (`-`, `.`, `""`) to confirm it does not crash.
- `Vocab.to_text` was tested against a small sample vocabulary containing `Ġ`, `Ċ`, multi-byte characters, a cut multi-byte sequence and a missing ID.
- Error handling was tested with an empty function-definition file, and with an unexpected exception raised inside `Pipeline.run()`.
- `flake8 .` passes with no errors.
- TODO: confirm that `mypy .` with the required flags passes with no errors.
- TODO: compare the output with the expected answers for the provided prompts, and check edge cases (empty strings, large numbers, special characters, ambiguous prompts).

## Resources

- R. Sennrich, B. Haddow, A. Birch, "Neural Machine Translation of Rare Words with Subword Units" (2016): BPE
- A. Radford et al., "Language Models are Unsupervised Multitask Learners" (2019): byte-level BPE (GPT-2)
- B. Willard, R. Louf, "Efficient Guided Generation for Large Language Models" (2023): constrained decoding
- Qwen3-0.6B model card: https://huggingface.co/Qwen/Qwen3-0.6B
- Pydantic documentation: https://docs.pydantic.dev/
- uv documentation: https://docs.astral.sh/uv/

### Use of AI

- TODO: describe which tasks you used AI for and which parts of the project.
