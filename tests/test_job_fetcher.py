"""Tests for JobFetcher SSRF protections and metadata extraction."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.job_fetcher import (
    FetchResult,
    JobFetcher,
    JobFetcherError,
    _is_safe_ip,
    _parse_title_string,
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


# ── _parse_title_string ──────────────────────────────────────────────────────


class TestParseTitleString:
    def test_dash_delimited_three_parts(self):
        t, c, l = _parse_title_string("Senior Dev - Acme Corp - Kuala Lumpur, Malaysia")
        assert t == "Senior Dev"
        assert c == "Acme Corp"
        assert l == "Kuala Lumpur, Malaysia"

    def test_pipe_delimited_three_parts(self):
        t, c, l = _parse_title_string("Backend Engineer | Google | Mountain View, CA")
        assert t == "Backend Engineer"
        assert c == "Google"
        assert l == "Mountain View, CA"

    def test_dash_delimited_two_parts(self):
        t, c, l = _parse_title_string("ML Engineer - OpenAI")
        assert t == "ML Engineer"
        assert c == "OpenAI"
        assert l == ""

    def test_at_pattern(self):
        t, c, l = _parse_title_string("DevOps Engineer at Amazon in Seattle")
        assert t == "DevOps Engineer"
        assert c == "Amazon"
        assert l == "Seattle"

    def test_at_pattern_no_location(self):
        t, c, l = _parse_title_string("Data Scientist at Meta")
        assert t == "Data Scientist"
        assert c == "Meta"
        assert l == ""

    def test_hiring_pattern(self):
        t, c, l = _parse_title_string("Acme Corp is hiring a Senior Engineer in London")
        assert t == "Senior Engineer"
        assert c == "Acme Corp"
        assert l == "London"

    def test_no_delimiter_returns_title_only(self):
        t, c, l = _parse_title_string("Just a job title")
        assert t == "Just a job title"
        assert c == ""
        assert l == ""

    def test_empty_string(self):
        t, c, l = _parse_title_string("")
        assert t == "" and c == "" and l == ""

    def test_em_dash_delimited(self):
        t, c, l = _parse_title_string("Frontend Dev — Shopify — Toronto, ON")
        assert t == "Frontend Dev"
        assert c == "Shopify"
        assert l == "Toronto, ON"


# ── _extract_metadata ────────────────────────────────────────────────────────


class TestExtractMetadata:
    def test_extracts_from_title_tag(self):
        html = "<html><head><title>Senior Dev - Acme Corp - Remote</title></head><body></body></html>"
        t, c, l = JobFetcher._extract_metadata(html)
        assert t == "Senior Dev"
        assert c == "Acme Corp"
        assert l == "Remote"

    def test_extracts_from_og_title(self):
        html = """
        <html><head>
        <meta property="og:title" content="ML Engineer | DeepMind | London">
        </head><body></body></html>
        """
        t, c, l = JobFetcher._extract_metadata(html)
        assert t == "ML Engineer"
        assert c == "DeepMind"
        assert l == "London"

    def test_extracts_from_h1_when_no_title(self):
        html = "<html><head><title></title></head><body><h1>Backend Engineer at Stripe</h1></body></html>"
        t, c, l = JobFetcher._extract_metadata(html)
        assert t == "Backend Engineer"
        assert c == "Stripe"

    def test_jsonld_job_posting(self):
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "JobPosting", "title": "SRE", "organization": {"name": "Netflix"},
         "jobLocation": {"address": {"addressLocality": "Los Gatos", "addressRegion": "CA", "addressCountry": "US"}}}
        </script>
        </head><body></body></html>
        """
        t, c, l = JobFetcher._extract_metadata(html)
        assert t == "SRE"
        assert c == "Netflix"
        assert "Los Gatos" in l

    def test_og_site_name_used_for_company(self):
        html = """
        <html><head>
        <title>Software Engineer - TechStart</title>
        <meta property="og:site_name" content="TechStart">
        </head><body></body></html>
        """
        t, c, l = JobFetcher._extract_metadata(html)
        assert t == "Software Engineer"
        assert c == "TechStart"

    def test_job_board_site_name_not_used_as_company(self):
        html = """
        <html><head>
        <title>Software Engineer - Acme Corp</title>
        <meta property="og:site_name" content="Indeed">
        </head><body></body></html>
        """
        t, c, l = JobFetcher._extract_metadata(html)
        assert t == "Software Engineer"
        assert c == "Acme Corp"

    def test_empty_html(self):
        t, c, l = JobFetcher._extract_metadata("")
        assert t == "" and c == "" and l == ""

    def test_returns_fetch_result_dataclass(self):
        result = FetchResult(text="Job description text", title="Dev", company="Co", location="NYC")
        assert result.text == "Job description text"
        assert result.title == "Dev"
        assert result.company == "Co"
        assert result.location == "NYC"
