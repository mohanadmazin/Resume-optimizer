"""Tests for JobFetcher SSRF protections and metadata extraction."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.job_fetcher import (
    FetchResult,
    JobFetcher,
    JobFetcherError,
    _connect_to_ip,
    _parse_title_string,
    _resolve_and_validate,
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


# ── _resolve_and_validate ────────────────────────────────────────────────────


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_localhost(mock_dns):
    mock_dns.return_value = [(2, 1, 6, "", ("127.0.0.1", 0))]
    with pytest.raises(JobFetcherError, match="private/reserved"):
        _resolve_and_validate("localhost")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_loopback(mock_dns):
    mock_dns.return_value = [(2, 1, 6, "", ("127.0.0.1", 0))]
    with pytest.raises(JobFetcherError, match="private/reserved"):
        _resolve_and_validate("some-host")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_private_10(mock_dns):
    mock_dns.return_value = [(2, 1, 6, "", ("10.0.0.1", 0))]
    with pytest.raises(JobFetcherError, match="private/reserved"):
        _resolve_and_validate("internal-host")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_private_192(mock_dns):
    mock_dns.return_value = [(2, 1, 6, "", ("192.168.1.1", 0))]
    with pytest.raises(JobFetcherError, match="private/reserved"):
        _resolve_and_validate("router")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_private_172(mock_dns):
    mock_dns.return_value = [(2, 1, 6, "", ("172.16.0.1", 0))]
    with pytest.raises(JobFetcherError, match="private/reserved"):
        _resolve_and_validate("container-host")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_link_local(mock_dns):
    mock_dns.return_value = [(2, 1, 6, "", ("169.254.1.1", 0))]
    with pytest.raises(JobFetcherError, match="private/reserved"):
        _resolve_and_validate("link-local-host")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_multicast(mock_dns):
    mock_dns.return_value = [(2, 1, 6, "", ("224.0.0.1", 0))]
    with pytest.raises(JobFetcherError, match="private/reserved"):
        _resolve_and_validate("multicast-host")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_reserved(mock_dns):
    mock_dns.return_value = [(2, 1, 6, "", ("0.0.0.0", 0))]
    with pytest.raises(JobFetcherError, match="private/reserved"):
        _resolve_and_validate("zero-host")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_ipv6_loopback(mock_dns):
    mock_dns.return_value = [(10, 1, 6, "", ("::1", 0, 0, 0))]
    with pytest.raises(JobFetcherError, match="private/reserved"):
        _resolve_and_validate("ipv6-localhost")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_ipv6_private(mock_dns):
    mock_dns.return_value = [(10, 1, 6, "", ("fc00::1", 0, 0, 0))]
    with pytest.raises(JobFetcherError, match="private/reserved"):
        _resolve_and_validate("ipv6-ula")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_empty_results(mock_dns):
    mock_dns.return_value = []
    with pytest.raises(JobFetcherError, match="no results"):
        _resolve_and_validate("no-dns")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_dns_failure(mock_dns):
    mock_dns.side_effect = OSError("DNS resolution failed")
    with pytest.raises(JobFetcherError, match="DNS resolution failed"):
        _resolve_and_validate("unresolvable.example.com")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_accepts_public(mock_dns):
    mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
    ip = _resolve_and_validate("example.com")
    assert ip == "93.184.216.34"


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_rejects_if_any_record_is_private(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("93.184.216.34", 0)),
        (2, 1, 6, "", ("10.0.0.1", 0)),
    ]
    with pytest.raises(JobFetcherError, match="private/reserved"):
        _resolve_and_validate("dual-homed.example.com")


@patch("app.services.job_fetcher.socket.getaddrinfo")
def test_resolve_returns_first_ip(mock_dns):
    mock_dns.return_value = [
        (2, 1, 6, "", ("93.184.216.34", 0)),
        (2, 1, 6, "", ("93.184.216.35", 0)),
    ]
    ip = _resolve_and_validate("multi-homed.example.com")
    assert ip == "93.184.216.34"


def test_resolve_rejects_empty_hostname():
    with pytest.raises(JobFetcherError, match="no hostname"):
        _resolve_and_validate("")


# ── _validate_url ────────────────────────────────────────────────────────────


def test_validate_url_rejects_ftp():
    with pytest.raises(JobFetcherError, match="not allowed"):
        _validate_url("ftp://example.com/file")


def test_validate_url_rejects_file_scheme():
    with pytest.raises(JobFetcherError, match="not allowed"):
        _validate_url("file:///etc/passwd")


def test_validate_url_accepts_http():
    _validate_url("http://example.com/jobs")  # no exception


def test_validate_url_accepts_https():
    _validate_url("https://example.com/jobs")  # no exception


# ── JobFetcher.fetch_from_url ────────────────────────────────────────────────


def test_fetch_rejects_empty_url():
    with pytest.raises(JobFetcherError, match="empty"):
        JobFetcher.fetch_from_url("")


def test_fetch_rejects_whitespace_url():
    with pytest.raises(JobFetcherError, match="empty"):
        JobFetcher.fetch_from_url("   ")


@patch("app.services.job_fetcher._resolve_and_validate")
def test_fetch_rejects_private_ip(mock_resolve):
    mock_resolve.side_effect = JobFetcherError("private/reserved IP (169.254.169.254)")
    with pytest.raises(JobFetcherError, match="private/reserved"):
        JobFetcher.fetch_from_url("http://169.254.169.254/metadata")


def test_fetch_rejects_file_url():
    with pytest.raises(JobFetcherError):
        JobFetcher.fetch_from_url("file:///etc/passwd")


@patch("app.services.job_fetcher._resolve_and_validate", return_value="93.184.216.34")
def test_fetch_rejects_non_html_content_type(mock_resolve):
    mock_response = MagicMock()
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.status_code = 200
    mock_response.close = MagicMock()

    with patch("app.services.job_fetcher._connect_to_ip", return_value=mock_response):
        with pytest.raises(JobFetcherError, match="content type"):
            JobFetcher.fetch_from_url("https://example.com/api")


@patch("app.services.job_fetcher._resolve_and_validate", return_value="93.184.216.34")
def test_fetch_rejects_too_large_response(mock_resolve):
    mock_response = MagicMock()
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.status_code = 200
    mock_response.close = MagicMock()
    mock_response.content = b"x" * (6 * 1024 * 1024)

    with patch("app.services.job_fetcher._connect_to_ip", return_value=mock_response):
        with pytest.raises(JobFetcherError, match="MB limit"):
            JobFetcher.fetch_from_url("https://example.com/large")


@patch("app.services.job_fetcher._resolve_and_validate")
def test_fetch_redirect_to_private_rejected(mock_resolve):
    """A redirect that lands on a private IP must be rejected."""
    first_response = MagicMock()
    first_response.status_code = 302
    first_response.headers = {"Location": "http://10.0.0.1/secret"}
    first_response.close = MagicMock()

    def resolve_side_effect(hostname):
        if hostname == "10.0.0.1":
            raise JobFetcherError("private/reserved IP (10.0.0.1)")
        return "93.184.216.34"

    mock_resolve.side_effect = resolve_side_effect

    with patch("app.services.job_fetcher._connect_to_ip", return_value=first_response):
        with pytest.raises(JobFetcherError, match="private/reserved"):
            JobFetcher.fetch_from_url("https://example.com/redirect")


@patch("app.services.job_fetcher._resolve_and_validate", return_value="93.184.216.34")
def test_fetch_too_many_redirects(mock_resolve):
    """More than MAX_REDIRECTS must be rejected."""
    redirect_response = MagicMock()
    redirect_response.status_code = 302
    redirect_response.headers = {"Location": "https://example.com/loop"}
    redirect_response.close = MagicMock()

    with patch("app.services.job_fetcher._connect_to_ip", return_value=redirect_response):
        with pytest.raises(JobFetcherError, match="Too many redirects"):
            JobFetcher.fetch_from_url("https://example.com/start")


@patch("app.services.job_fetcher._resolve_and_validate", return_value="93.184.216.34")
def test_fetch_redirect_missing_location_rejected(mock_resolve):
    """A redirect without a Location header must be rejected."""
    redirect_response = MagicMock()
    redirect_response.status_code = 301
    redirect_response.headers = {}
    redirect_response.close = MagicMock()

    with patch("app.services.job_fetcher._connect_to_ip", return_value=redirect_response):
        with pytest.raises(JobFetcherError, match="missing Location"):
            JobFetcher.fetch_from_url("https://example.com/bad-redirect")


@patch("app.services.job_fetcher._resolve_and_validate", return_value="93.184.216.34")
def test_fetch_success(mock_resolve):
    """Successful fetch returns FetchResult with extracted content."""
    html = """
    <html><head><title>Dev - Acme Corp - Remote</title></head>
    <body><main>
    <p>We are looking for a senior developer.</p>
    <p>Requirements: Python, SQL, 5+ years.</p>
    </main></body></html>
    """
    mock_response = MagicMock()
    mock_response.headers = {"Content-Type": "text/html"}
    mock_response.status_code = 200
    mock_response.content = html.encode("utf-8")
    mock_response.close = MagicMock()

    with patch("app.services.job_fetcher._connect_to_ip", return_value=mock_response):
        result = JobFetcher.fetch_from_url("https://example.com/jobs/123")

    assert isinstance(result, FetchResult)
    assert "senior developer" in result.text.lower()
    assert result.title == "Dev"
    assert result.company == "Acme Corp"
    assert result.location == "Remote"


@patch("app.services.job_fetcher._resolve_and_validate", return_value="93.184.216.34")
def test_fetch_resolves_dns_once_per_redirect(mock_resolve):
    """Each redirect triggers a fresh DNS resolution and validation."""
    resp1 = MagicMock()
    resp1.status_code = 302
    resp1.headers = {"Location": "https://other-site.com/page"}
    resp1.close = MagicMock()

    html = "<html><head><title>Page</title></head><body><main>Content here.</main></body></html>"
    resp2 = MagicMock()
    resp2.headers = {"Content-Type": "text/html"}
    resp2.status_code = 200
    resp2.content = html.encode("utf-8")
    resp2.close = MagicMock()

    with patch("app.services.job_fetcher._connect_to_ip", side_effect=[resp1, resp2]):
        result = JobFetcher.fetch_from_url("https://example.com/start")

    assert result.text == "Content here."
    # DNS was resolved twice: once for example.com, once for other-site.com
    assert mock_resolve.call_count == 2
    mock_resolve.assert_any_call("example.com")
    mock_resolve.assert_any_call("other-site.com")


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

    def test_linkedin_hiring_pattern_in_title(self):
        """LinkedIn title: 'Company hiring Title in Location' (no a/an/for)."""
        html = '<html><head><title>HCLTech hiring Senior Network Engineer in Kuala Lumpur, Malaysia</title></head><body></body></html>'
        t, c, l = JobFetcher._extract_metadata(html)
        assert t == "Senior Network Engineer"
        assert c == "HCLTech"
        assert l == "Kuala Lumpur, Malaysia"

    def test_linkedin_site_name_filtered(self):
        """LinkedIn og:site_name should not become the company name."""
        html = """
        <html><head>
        <title>Dev - Acme Corp</title>
        <meta property="og:site_name" content="LinkedIn">
        </head><body></body></html>
        """
        t, c, l = JobFetcher._extract_metadata(html)
        assert c == "Acme Corp"

    def test_extract_clean_text_filters_noise(self):
        """Noise lines like 'Sign in', 'Join now' should be removed."""
        html = """
        <html><body>
        <main>
        <p>Senior Network Engineer</p>
        <p>HCLTech</p>
        <p>Sign in to see more</p>
        <p>Join now</p>
        <p>We are seeking a skilled engineer...</p>
        <p>Forgot password?</p>
        <p>Email or phone</p>
        </main>
        </body></html>
        """
        text = JobFetcher._extract_clean_text(html)
        assert "Sign in" not in text
        assert "Join now" not in text
        assert "Forgot password" not in text
        assert "Email or phone" not in text
        assert "Senior Network Engineer" in text
        assert "We are seeking" in text

    def test_extract_clean_text_removes_forms(self):
        """Form elements should be removed."""
        html = """
        <html><body>
        <main>
        <p>Job description text here.</p>
        <form><input type="text" placeholder="Email"><button>Submit</button></form>
        <p>More job details.</p>
        </main>
        </body></html>
        """
        text = JobFetcher._extract_clean_text(html)
        assert "Job description" in text
        assert "More job details" in text
        assert "Email" not in text
        assert "Submit" not in text
