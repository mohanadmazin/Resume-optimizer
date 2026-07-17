"""Tests for JobFetcher SSRF protections."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.job_fetcher import (
    JobFetcher,
    JobFetcherError,
    _is_safe_ip,
    _safe_url_for_log,
    _validate_url,
)


# ── _safe_url_for_log ────────────────────────────────────────────────────────


def test_safe_url_strips_query_params():
    url = "https://example.com/jobs?token=secret&id=42#section"
    assert _safe_url_for_log(url) == "https://example.com/jobs"


def test_safe_url_strips_fragment():
    url = "https://example.com/path#frag"
    assert _safe_url_for_log(url) == "https://example.com/path"


def test_safe_url_preserves_clean_url():
    url = "https://example.com/jobs/123"
    assert _safe_url_for_log(url) == "https://example.com/jobs/123"


# ── _is_safe_ip ──────────────────────────────────────────────────────────────


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_localhost(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("127.0.0.1", 0)),
    ]
    assert _is_safe_ip("localhost") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_loopback(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("127.0.0.1", 0)),
    ]
    assert _is_safe_ip("some-host") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_private_10(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("10.0.0.1", 0)),
    ]
    assert _is_safe_ip("internal-host") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_private_192(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("192.168.1.1", 0)),
    ]
    assert _is_safe_ip("router") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_private_172(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("172.16.0.1", 0)),
    ]
    assert _is_safe_ip("container-host") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_link_local(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("169.254.1.1", 0)),
    ]
    assert _is_safe_ip("link-local-host") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_multicast(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("224.0.0.1", 0)),
    ]
    assert _is_safe_ip("multicast-host") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_reserved(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("0.0.0.0", 0)),
    ]
    assert _is_safe_ip("zero-host") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_ipv6_loopback(mock_dns):
    mock_dns.return_value = [
        (10, 1, 6, "", ("::1", 0, 0, 0)),
    ]
    assert _is_safe_ip("ipv6-localhost") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_ipv6_private(mock_dns):
    mock_dns.return_value = [
        (10, 1, 6, "", ("fc00::1", 0, 0, 0)),
    ]
    assert _is_safe_ip("ipv6-ula") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_empty_results(mock_dns):
    mock_dns.return_value = []
    assert _is_safe_ip("no-dns") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_dns_failure(mock_dns):
    mock_dns.side_effect = OSError("DNS resolution failed")
    assert _is_safe_ip("unresolvable.example.com") is False


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_accepts_public(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("93.184.216.34", 0)),
    ]
    assert _is_safe_ip("example.com") is True


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_safe_ip_rejects_if_any_record_is_private(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("93.184.216.34", 0)),
        (2, 1, 6, "", ("10.0.0.1", 0)),
    ]
    assert _is_safe_ip("dual-homed.example.com") is False


# ── _validate_url ────────────────────────────────────────────────────────────


def test_validate_url_rejects_ftp():
    with pytest.raises(JobFetcherError, match="not allowed"):
        _validate_url("ftp://example.com/file")


def test_validate_url_rejects_file_scheme():
    with pytest.raises(JobFetcherError, match="not allowed"):
        _validate_url("file:///etc/passwd")


@patch("app.services.job_fetcher._is_safe_ip", return_value=False)
def test_validate_url_rejects_private_host(mock_safe):
    with pytest.raises(JobFetcherError, match="private or reserved"):
        _validate_url("http://internal-service.local/data")


@patch("app.services.job_fetcher._is_safe_ip", return_value=True)
def test_validate_url_accepts_public(mock_safe):
    _validate_url("https://example.com/jobs")  # no exception


# ── JobFetcher.fetch_from_url ────────────────────────────────────────────────


def test_fetch_rejects_empty_url():
    with pytest.raises(JobFetcherError, match="empty"):
        JobFetcher.fetch_from_url("")


def test_fetch_rejects_whitespace_url():
    with pytest.raises(JobFetcherError, match="empty"):
        JobFetcher.fetch_from_url("   ")


@patch("app.services.job_fetcher._is_safe_ip", return_value=False)
def test_fetch_rejects_private_ip(mock_safe):
    with pytest.raises(JobFetcherError, match="private or reserved"):
        JobFetcher.fetch_from_url("http://169.254.169.254/metadata")


def test_fetch_rejects_file_url():
    with pytest.raises(JobFetcherError):
        JobFetcher.fetch_from_url("file:///etc/passwd")


@patch("app.services.job_fetcher._is_safe_ip", return_value=True)
def test_fetch_rejects_non_html_content_type(mock_safe):
    mock_response = MagicMock()
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.close = MagicMock()
    mock_response.iter_content = MagicMock(return_value=[])

    with patch("app.services.job_fetcher.requests.Session") as mock_session_cls:
        session = MagicMock()
        session.get.return_value = mock_response
        mock_session_cls.return_value = session

        with pytest.raises(JobFetcherError, match="content type"):
            JobFetcher.fetch_from_url("https://example.com/api")


@patch("app.services.job_fetcher._is_safe_ip", return_value=True)
def test_fetch_rejects_too_large_response(mock_safe):
    mock_response = MagicMock()
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.close = MagicMock()
    # Return 6 MB of data to exceed the 5 MB limit
    mock_response.content = b"x" * (6 * 1024 * 1024)

    with patch("app.services.job_fetcher.requests.Session") as mock_session_cls:
        session = MagicMock()
        session.get.return_value = mock_response
        mock_session_cls.return_value = session

        with pytest.raises(JobFetcherError, match="MB limit"):
            JobFetcher.fetch_from_url("https://example.com/large")


def test_fetch_redirect_to_private_rejected():
    """A redirect that lands on a private IP must be rejected."""
    # First request to public host — returns 302 to private host
    first_response = MagicMock()
    first_response.status_code = 302
    first_response.headers = {"Location": "http://10.0.0.1/secret"}
    first_response.close = MagicMock()

    def _safe_by_host(hostname):
        return hostname != "10.0.0.1"

    with (
        patch("app.services.job_fetcher._is_safe_ip", side_effect=_safe_by_host),
        patch("app.services.job_fetcher.requests.Session") as mock_session_cls,
    ):
        session = MagicMock()
        session.get.return_value = first_response
        mock_session_cls.return_value = session

        with pytest.raises(JobFetcherError, match="private or reserved"):
            JobFetcher.fetch_from_url("https://example.com/redirect")


@patch("app.services.job_fetcher._is_safe_ip", return_value=True)
def test_fetch_too_many_redirects(mock_safe):
    """More than MAX_REDIRECTS must be rejected."""
    redirect_response = MagicMock()
    redirect_response.status_code = 302
    redirect_response.headers = {"Location": "https://example.com/loop"}
    redirect_response.close = MagicMock()

    with patch("app.services.job_fetcher.requests.Session") as mock_session_cls:
        session = MagicMock()
        session.get.return_value = redirect_response
        mock_session_cls.return_value = session

        with pytest.raises(JobFetcherError, match="Too many redirects"):
            JobFetcher.fetch_from_url("https://example.com/start")


@patch("app.services.job_fetcher._is_safe_ip", return_value=True)
def test_fetch_redirect_missing_location_rejected(mock_safe):
    """A redirect without a Location header must be rejected."""
    redirect_response = MagicMock()
    redirect_response.status_code = 301
    redirect_response.headers = {}  # No Location
    redirect_response.close = MagicMock()

    with patch("app.services.job_fetcher.requests.Session") as mock_session_cls:
        session = MagicMock()
        session.get.return_value = redirect_response
        mock_session_cls.return_value = session

        with pytest.raises(JobFetcherError, match="missing Location"):
            JobFetcher.fetch_from_url("https://example.com/bad-redirect")
