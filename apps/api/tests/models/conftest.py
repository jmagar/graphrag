"""
Minimal conftest for model tests.

This conftest bypasses the main app initialization since model tests
don't require the full application context.
"""


# No fixtures needed for basic Pydantic model tests
# Models can be imported and tested directly
