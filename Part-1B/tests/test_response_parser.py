"""Tests for parsing structured AI model responses."""

import pytest

from k8s_review.response_parser import (
    ModelResponseParseError,
    parse_model_response,
)


def test_parse_valid_json_response():
    """A valid JSON object should be parsed successfully."""
    content = '{"review_summary": "Review complete", "findings": []}'

    result = parse_model_response(content)

    assert result["review_summary"] == "Review complete"
    assert result["findings"] == []


def test_reject_malformed_json():
    """Malformed JSON should raise a clear parsing error."""
    with pytest.raises(ModelResponseParseError, match="invalid JSON"):
        parse_model_response('{"review_summary": "Incomplete"')


def test_reject_empty_response():
    """An empty response should be rejected."""
    with pytest.raises(ModelResponseParseError, match="empty"):
        parse_model_response("")


def test_reject_json_array():
    """A JSON array should be rejected because an object is required."""
    with pytest.raises(ModelResponseParseError, match="JSON object"):
        parse_model_response('[{"finding": "example"}]')
