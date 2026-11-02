import time

import pytest

from plai.validation import is_valid_email


@pytest.mark.parametrize(
    "email", ["ana@example.com", "a.b+tag@sub.example.co", "x@y.z"]
)
def test_valid_emails(email):
    assert is_valid_email(email)


@pytest.mark.parametrize(
    "email",
    [
        "",
        "plain",
        "@example.com",
        "ana@",
        "ana@example",
        "ana@.com",
        "ana@example.",
        "ana@exa..mple.com",
        "a@b@example.com",
        "ana smith@example.com",
        "ana@exam ple.com",
        "a@" + "b" * 260 + ".com",
    ],
)
def test_invalid_emails(email):
    assert not is_valid_email(email)


def test_pathological_input_is_fast():
    # The input CodeQL flagged for the old regex: many repetitions of '!.' after '!@!.'
    start = time.perf_counter()
    assert not is_valid_email("!@!." + "!." * 100_000)
    assert time.perf_counter() - start < 0.5
