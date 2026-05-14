"""Core package.

Keep this package initializer lightweight. Importing shared modules such as
``core.logger`` or ``core.security`` should not eagerly load the LLM stack.
"""

__all__: list[str] = []
