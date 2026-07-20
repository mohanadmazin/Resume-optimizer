"""Tests for the job fetching subsystem (security, extraction, metadata, fetcher)."""

from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from app.infrastructure.html_extractor import extract_text_from_html, extract_text_from_soup
from app.infrastructure.metadata import (
    JobMetadata,
    TitleCandidate,
    extract_jsonld,
    extract_metadata,
    parse_title_string,
)
from app.infrastructure.security import (
    SSRFError,
    BLOCKED_PORTS,
    ResolvedTarget,
    resolve_and_validate,
    validate_port,
    validate_scheme,
)

# Keep backward-compatible aliases for the orchestrator tests
from app.infrastructure.job_fetcher import (
    FetchResult,
    InvalidURLError,
    JobFetcherError,
    fetch_from_url,
    fetch_job,
    _build_host_header,
    _pinned_getaddrinfo,
)


def test_http_host_header_uses_http_default_port():
    assert _build_host_header("example.com", 80, "http") == "example.com"


def test_ipv6_pinned_resolution_has_valid_sockaddr():
    pinned = _pinned_getaddrinfo(MagicMock(), "2001:db8::1", "example.com", 443)
    assert pinned("example.com", 443)[0][4] == ("2001:db8::1", 443, 0, 0)


def test_unexpected_fetch_exception_is_not_silenced():
    with patch("app.infrastructure.job_fetcher.fetch_from_url", side_effect=RuntimeError("bug")):
        with pytest.raises(RuntimeError, match="bug"):
            fetch_job("https://example.com/job")


# ═══════════════════════════════════════════════════════════════════════════════
# security.py tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidateScheme:
    def test_rejects_ftp(self):
        with pytest.raises(SSRFError, match="not allowed"):
            validate_scheme("ftp://example.com/file")

    def test_rejects_file(self):
        with pytest.raises(SSRFError, match="not allowed"):
            validate_scheme("file:///etc/passwd")

    def test_accepts_http(self):
        validate_scheme("http://example.com/jobs")

    def test_accepts_https(self):
        validate_scheme("https://example.com/jobs")


class TestValidatePort:
    def test_rejects_ssh(self):
        with pytest.raises(SSRFError, match="blocked"):
            validate_port("https://example.com:22/path")

    def test_rejects_mysql(self):
        with pytest.raises(SSRFError, match="blocked"):
            validate_port("https://example.com:3306/db")

    def test_rejects_redis(self):
        with pytest.raises(SSRFError, match="blocked"):
            validate_port("https://example.com:6379/key")

    def test_rejects_mongodb(self):
        with pytest.raises(SSRFError, match="blocked"):
            validate_port("https://example.com:27017/data")

    def test_accepts_standard_ports(self):
        validate_port("https://example.com:443/path")
        validate_port("http://example.com:80/path")

    def test_accepts_common_web_ports(self):
        validate_port("https://example.com:8080/path")
        validate_port("https://example.com:3000/path")


class TestResolveAndValidate:
    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_localhost(self, mock_dns):
        mock_dns.return_value = [(2, 1, 6, "", ("127.0.0.1", 0))]
        with pytest.raises(SSRFError, match="private/reserved"):
            resolve_and_validate("http://localhost/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_private_10(self, mock_dns):
        mock_dns.return_value = [(2, 1, 6, "", ("10.0.0.1", 0))]
        with pytest.raises(SSRFError, match="private/reserved"):
            resolve_and_validate("http://internal-host/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_private_192(self, mock_dns):
        mock_dns.return_value = [(2, 1, 6, "", ("192.168.1.1", 0))]
        with pytest.raises(SSRFError, match="private/reserved"):
            resolve_and_validate("http://router/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_private_172(self, mock_dns):
        mock_dns.return_value = [(2, 1, 6, "", ("172.16.0.1", 0))]
        with pytest.raises(SSRFError, match="private/reserved"):
            resolve_and_validate("http://container/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_link_local(self, mock_dns):
        mock_dns.return_value = [(2, 1, 6, "", ("169.254.1.1", 0))]
        with pytest.raises(SSRFError, match="private/reserved"):
            resolve_and_validate("http://link-local/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_multicast(self, mock_dns):
        mock_dns.return_value = [(2, 1, 6, "", ("224.0.0.1", 0))]
        with pytest.raises(SSRFError, match="private/reserved"):
            resolve_and_validate("http://multicast/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_reserved(self, mock_dns):
        mock_dns.return_value = [(2, 1, 6, "", ("0.0.0.0", 0))]
        with pytest.raises(SSRFError, match="private/reserved"):
            resolve_and_validate("http://zero-host/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_ipv6_loopback(self, mock_dns):
        mock_dns.return_value = [(10, 1, 6, "", ("::1", 0, 0, 0))]
        with pytest.raises(SSRFError, match="private/reserved"):
            resolve_and_validate("http://ipv6-localhost/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_ipv6_private(self, mock_dns):
        mock_dns.return_value = [(10, 1, 6, "", ("fc00::1", 0, 0, 0))]
        with pytest.raises(SSRFError, match="private/reserved"):
            resolve_and_validate("http://ipv6-ula/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_empty_results(self, mock_dns):
        mock_dns.return_value = []
        with pytest.raises(SSRFError, match="no results"):
            resolve_and_validate("http://no-dns.example.com/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_dns_failure(self, mock_dns):
        mock_dns.side_effect = OSError("DNS failed")
        with pytest.raises(SSRFError, match="DNS resolution failed"):
            resolve_and_validate("http://unresolvable.example.com/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_accepts_public_ip(self, mock_dns):
        mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 0))]
        target = resolve_and_validate("https://example.com/jobs")
        assert isinstance(target, ResolvedTarget)
        assert target.ip == "93.184.216.34"
        assert target.hostname == "example.com"
        assert target.scheme == "https"

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_rejects_if_any_record_is_private(self, mock_dns):
        mock_dns.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0)),
            (2, 1, 6, "", ("10.0.0.1", 0)),
        ]
        with pytest.raises(SSRFError, match="private/reserved"):
            resolve_and_validate("http://dual-homed.example.com/page")

    @patch("app.infrastructure.security.socket.getaddrinfo")
    def test_returns_first_ip(self, mock_dns):
        mock_dns.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0)),
            (2, 1, 6, "", ("93.184.216.35", 0)),
        ]
        target = resolve_and_validate("http://multi.example.com/page")
        assert target.ip == "93.184.216.34"

    def test_rejects_empty_hostname(self):
        with pytest.raises(SSRFError, match="no hostname"):
            resolve_and_validate("http:///path")

    def test_blocked_ports_is_frozen(self):
        assert isinstance(BLOCKED_PORTS, frozenset)
        assert 22 in BLOCKED_PORTS
        assert 3306 in BLOCKED_PORTS
        assert 6379 in BLOCKED_PORTS


# ═══════════════════════════════════════════════════════════════════════════════
# html_extractor.py tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractText:
    def test_extracts_from_main(self):
        html = "<html><body><main><p>Hello world.</p></main></body></html>"
        text = extract_text_from_html(html)
        assert "Hello world" in text

    def test_removes_forms(self):
        html = """
        <html><body><main>
        <p>Job text.</p>
        <form><input type="text"><button>Submit</button></form>
        <p>More text.</p>
        </main></body></html>
        """
        text = extract_text_from_html(html)
        assert "Job text" in text
        assert "More text" in text
        assert "Submit" not in text

    def test_removes_noise_lines(self):
        html = """
        <html><body><main>
        <p>Senior Engineer</p>
        <p>Sign in to see more</p>
        <p>Join now</p>
        <p>We are hiring.</p>
        <p>Forgot password?</p>
        </main></body></html>
        """
        text = extract_text_from_html(html)
        assert "Senior Engineer" in text
        assert "We are hiring" in text
        assert "Sign in" not in text
        assert "Join now" not in text
        assert "Forgot password" not in text

    def test_empty_html(self):
        assert extract_text_from_html("") == ""

    def test_no_main_body_fallback(self):
        html = "<html><body><p>Some content here.</p></body></html>"
        text = extract_text_from_html(html)
        assert "Some content" in text

    def test_from_soup_avoids_double_parse(self):
        html = "<html><head><title>X</title></head><body><main><p>Content.</p></main></body></html>"
        soup = BeautifulSoup(html, "lxml")
        text = extract_text_from_soup(soup)
        assert "Content" in text


# ═══════════════════════════════════════════════════════════════════════════════
# metadata.py tests — parse_title_string
# ═══════════════════════════════════════════════════════════════════════════════


class TestParseTitleString:
    def test_dash_three_parts(self):
        c = parse_title_string("Senior Dev - Acme Corp - Kuala Lumpur, Malaysia")
        assert c.title == "Senior Dev"
        assert c.company == "Acme Corp"
        assert c.location == "Kuala Lumpur, Malaysia"
        assert c.confidence >= 0.70

    def test_pipe_three_parts(self):
        c = parse_title_string("Backend Engineer | Google | Mountain View, CA")
        assert c.title == "Backend Engineer"
        assert c.company == "Google"
        assert c.location == "Mountain View, CA"

    def test_dash_two_parts(self):
        c = parse_title_string("ML Engineer - OpenAI")
        assert c.title == "ML Engineer"
        assert c.company == "OpenAI"
        assert c.location == ""

    def test_at_pattern(self):
        c = parse_title_string("DevOps Engineer at Amazon in Seattle")
        assert c.title == "DevOps Engineer"
        assert c.company == "Amazon"
        assert c.location == "Seattle"

    def test_at_pattern_no_location(self):
        c = parse_title_string("Data Scientist at Meta")
        assert c.title == "Data Scientist"
        assert c.company == "Meta"

    def test_hiring_pattern_with_article(self):
        c = parse_title_string("Acme Corp is hiring a Senior Engineer in London")
        assert c.title == "Senior Engineer"
        assert c.company == "Acme Corp"
        assert c.location == "London"

    def test_hiring_pattern_without_article(self):
        c = parse_title_string("HCLTech hiring Senior Network Engineer in Kuala Lumpur")
        assert c.title == "Senior Network Engineer"
        assert c.company == "HCLTech"
        assert c.location == "Kuala Lumpur"

    def test_em_dash_delimited(self):
        c = parse_title_string("Frontend Dev — Shopify — Toronto, ON")
        assert c.title == "Frontend Dev"
        assert c.company == "Shopify"
        assert c.location == "Toronto, ON"

    def test_no_delimiter_returns_title_only(self):
        c = parse_title_string("Just a job title")
        assert c.title == "Just a job title"
        assert c.company == ""

    def test_empty_string(self):
        c = parse_title_string("")
        assert c.title == "" and c.company == "" and c.confidence == 0.0

    def test_returns_highest_confidence(self):
        """Structured patterns score higher than delimiter splits."""
        c = parse_title_string("Dev at Google in NYC")
        assert c.confidence >= 0.90  # at-pattern

    def test_is_title_candidate(self):
        c = parse_title_string("Dev - Co")
        assert isinstance(c, TitleCandidate)


# ═══════════════════════════════════════════════════════════════════════════════
# metadata.py tests — extract_metadata / extract_jsonld
# ═══════════════════════════════════════════════════════════════════════════════


class TestExtractJsonLd:
    def test_extracts_job_posting(self):
        html = """
        <html><head>
        <script type="application/ld+json">
        {"@type": "JobPosting", "title": "SRE", "organization": {"name": "Netflix"},
         "jobLocation": {"address": {"addressLocality": "Los Gatos", "addressRegion": "CA", "addressCountry": "US"}}}
        </script>
        </head><body></body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        data = extract_jsonld(soup)
        assert data.title == "SRE"
        assert data.company == "Netflix"
        assert "Los Gatos" in data.location

    def test_returns_empty_when_no_jsonld(self):
        html = "<html><body></body></html>"
        soup = BeautifulSoup(html, "lxml")
        data = extract_jsonld(soup)
        assert data.title == "" and data.company == ""


class TestExtractMetadata:
    def test_from_title_tag(self):
        html = "<html><head><title>Senior Dev - Acme Corp - Remote</title></head><body></body></html>"
        soup = BeautifulSoup(html, "lxml")
        m = extract_metadata(soup)
        assert m.title == "Senior Dev"
        assert m.company == "Acme Corp"
        assert m.location == "Remote"

    def test_from_og_title(self):
        html = """
        <html><head>
        <meta property="og:title" content="ML Engineer | DeepMind | London">
        </head><body></body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        m = extract_metadata(soup)
        assert m.title == "ML Engineer"
        assert m.company == "DeepMind"
        assert m.location == "London"

    def test_from_h1_when_no_title(self):
        html = "<html><head><title></title></head><body><h1>Backend Engineer at Stripe</h1></body></html>"
        soup = BeautifulSoup(html, "lxml")
        m = extract_metadata(soup)
        assert m.title == "Backend Engineer"
        assert m.company == "Stripe"

    def test_jsonld_overrides_title_tag(self):
        html = """
        <html><head>
        <title>Wrong - FakeCo</title>
        <script type="application/ld+json">
        {"@type": "JobPosting", "title": "Correct Title", "organization": {"name": "RealCo"}}
        </script>
        </head><body></body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        m = extract_metadata(soup)
        assert m.title == "Correct Title"
        assert m.company == "RealCo"

    def test_og_site_name_used_for_company(self):
        html = """
        <html><head>
        <title>Software Engineer - TechStart</title>
        <meta property="og:site_name" content="TechStart">
        </head><body></body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        m = extract_metadata(soup)
        assert m.company == "TechStart"

    def test_job_board_site_name_filtered(self):
        html = """
        <html><head>
        <title>Software Engineer - Acme Corp</title>
        <meta property="og:site_name" content="Indeed">
        </head><body></body></html>
        """
        soup = BeautifulSoup(html, "lxml")
        m = extract_metadata(soup)
        assert m.company == "Acme Corp"

    def test_linkedin_hiring_pattern(self):
        html = '<html><head><title>HCLTech hiring Senior Network Engineer in Kuala Lumpur</title></head><body></body></html>'
        soup = BeautifulSoup(html, "lxml")
        m = extract_metadata(soup)
        assert m.title == "Senior Network Engineer"
        assert m.company == "HCLTech"
        assert m.location == "Kuala Lumpur"

    def test_empty_html(self):
        soup = BeautifulSoup("", "lxml")
        m = extract_metadata(soup)
        assert m.title == "" and m.company == "" and m.location == ""

    def test_returns_job_metadata(self):
        soup = BeautifulSoup("<html><body></body></html>", "lxml")
        assert isinstance(extract_metadata(soup), JobMetadata)


# ═══════════════════════════════════════════════════════════════════════════════
# job_fetcher.py orchestrator tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestFetchFromUrl:
    def test_rejects_empty_url(self):
        with pytest.raises(InvalidURLError, match="empty"):
            fetch_from_url("")

    def test_rejects_whitespace_url(self):
        with pytest.raises(InvalidURLError, match="empty"):
            fetch_from_url("   ")

    def test_rejects_file_url(self):
        with pytest.raises(InvalidURLError):
            fetch_from_url("file:///etc/passwd")

    def test_rejects_ftp_url(self):
        with pytest.raises(InvalidURLError, match="not allowed"):
            fetch_from_url("ftp://example.com/file")

    def test_rejects_mailto(self):
        with pytest.raises(InvalidURLError, match="not allowed"):
            fetch_from_url("mailto:user@example.com")

    def test_rejects_blocked_port(self):
        with pytest.raises(InvalidURLError, match="blocked"):
            fetch_from_url("https://example.com:22/path")

    @patch("app.infrastructure.job_fetcher.resolve_and_validate")
    def test_rejects_private_ip(self, mock_resolve):
        mock_resolve.side_effect = SSRFError("private/reserved IP (169.254.169.254)")
        with pytest.raises(InvalidURLError, match="private/reserved"):
            fetch_from_url("http://169.254.169.254/metadata")

    @patch("app.infrastructure.job_fetcher.resolve_and_validate", return_value=ResolvedTarget(
        hostname="example.com", ip="93.184.216.34", port=443, scheme="https",
    ))
    def test_rejects_non_html_content_type(self, mock_resolve):
        resp = MagicMock()
        resp.headers = {"Content-Type": "application/json"}
        resp.status_code = 200
        resp.close = MagicMock()
        with patch("app.infrastructure.job_fetcher._connect", return_value=resp):
            with pytest.raises(JobFetcherError, match="content type"):
                fetch_from_url("https://example.com/api")

    @patch("app.infrastructure.job_fetcher.resolve_and_validate", return_value=ResolvedTarget(
        hostname="example.com", ip="93.184.216.34", port=443, scheme="https",
    ))
    def test_rejects_too_large_response(self, mock_resolve):
        resp = MagicMock()
        resp.headers = {"Content-Type": "text/html", "Content-Length": str(6 * 1024 * 1024)}
        resp.status_code = 200
        resp.close = MagicMock()
        resp.content = b"x" * (6 * 1024 * 1024)
        resp.iter_content.return_value = [b"x" * (6 * 1024 * 1024)]
        with patch("app.infrastructure.job_fetcher._connect", return_value=resp):
            with pytest.raises(JobFetcherError, match="MB limit"):
                fetch_from_url("https://example.com/large")

    @patch("app.infrastructure.job_fetcher.resolve_and_validate", return_value=ResolvedTarget(
        hostname="example.com", ip="93.184.216.34", port=443, scheme="https",
    ))
    def test_success(self, mock_resolve):
        html = """
        <html><head><title>Dev - Acme Corp - Remote</title></head>
        <body><main>
        <p>We are looking for a senior developer with Python experience.</p>
        </main></body></html>
        """
        resp = MagicMock()
        resp.headers = {"Content-Type": "text/html"}
        resp.status_code = 200
        resp.content = html.encode("utf-8")
        resp.iter_content.return_value = [html.encode("utf-8")]
        resp.close = MagicMock()
        with patch("app.infrastructure.job_fetcher._connect", return_value=resp):
            result = fetch_from_url("https://example.com/jobs/123")
        assert isinstance(result, FetchResult)
        assert "senior developer" in result.text.lower()
        assert result.title == "Dev"
        assert result.company == "Acme Corp"
        assert result.location == "Remote"
        assert result.source_url == "https://example.com/jobs/123"

    @patch("app.infrastructure.job_fetcher.resolve_and_validate")
    def test_redirect_to_private_rejected(self, mock_resolve):
        resp1 = MagicMock()
        resp1.status_code = 302
        resp1.headers = {"Location": "http://10.0.0.1/secret"}
        resp1.close = MagicMock()

        def resolve_side_effect(url):
            if "10.0.0.1" in url:
                raise SSRFError("private/reserved IP (10.0.0.1)")
            return ResolvedTarget(hostname="example.com", ip="93.184.216.34", port=443, scheme="https")

        mock_resolve.side_effect = resolve_side_effect
        with patch("app.infrastructure.job_fetcher._connect", return_value=resp1):
            with pytest.raises(InvalidURLError, match="private/reserved"):
                fetch_from_url("https://example.com/redirect")

    @patch("app.infrastructure.job_fetcher.resolve_and_validate", return_value=ResolvedTarget(
        hostname="example.com", ip="93.184.216.34", port=443, scheme="https",
    ))
    def test_redirected_blocked_port_is_rejected(self, mock_resolve):
        resp1 = MagicMock()
        resp1.status_code = 302
        resp1.headers = {"Location": "https://evil.com:22/secret"}
        resp1.close = MagicMock()
        with patch("app.infrastructure.job_fetcher._connect", return_value=resp1):
            with pytest.raises(InvalidURLError, match="blocked"):
                fetch_from_url("https://example.com/start")

    @patch("app.infrastructure.job_fetcher.resolve_and_validate", return_value=ResolvedTarget(
        hostname="example.com", ip="93.184.216.34", port=443, scheme="https",
    ))
    def test_too_many_redirects(self, mock_resolve):
        resp = MagicMock()
        resp.status_code = 302
        resp.headers = {"Location": "https://example.com/loop"}
        resp.close = MagicMock()
        with patch("app.infrastructure.job_fetcher._connect", return_value=resp):
            with pytest.raises(JobFetcherError, match="Too many redirects"):
                fetch_from_url("https://example.com/start")

    @patch("app.infrastructure.job_fetcher.resolve_and_validate", return_value=ResolvedTarget(
        hostname="example.com", ip="93.184.216.34", port=443, scheme="https",
    ))
    def test_redirect_missing_location(self, mock_resolve):
        resp = MagicMock()
        resp.status_code = 301
        resp.headers = {}
        resp.close = MagicMock()
        with patch("app.infrastructure.job_fetcher._connect", return_value=resp):
            with pytest.raises(JobFetcherError, match="missing Location"):
                fetch_from_url("https://example.com/bad-redirect")

    @patch("app.infrastructure.job_fetcher.resolve_and_validate")
    def test_resolves_dns_per_redirect(self, mock_resolve):
        resp1 = MagicMock()
        resp1.status_code = 302
        resp1.headers = {"Location": "https://other-site.com/page"}
        resp1.close = MagicMock()

        html = "<html><head><title>Page</title></head><body><main>We are looking for a senior developer with strong experience.</main></body></html>"
        resp2 = MagicMock()
        resp2.headers = {"Content-Type": "text/html"}
        resp2.status_code = 200
        resp2.content = html.encode("utf-8")
        resp2.iter_content.return_value = [html.encode("utf-8")]
        resp2.close = MagicMock()

        mock_resolve.side_effect = [
            ResolvedTarget(hostname="example.com", ip="93.184.216.34", port=443, scheme="https"),
            ResolvedTarget(hostname="other-site.com", ip="93.184.216.35", port=443, scheme="https"),
        ]
        with patch("app.infrastructure.job_fetcher._connect", side_effect=[resp1, resp2]):
            result = fetch_from_url("https://example.com/start")
        assert result.text == "We are looking for a senior developer with strong experience."


# ═══════════════════════════════════════════════════════════════════════════════
# fetch_job() — graceful degradation tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestFetchJob:
    def test_success_returns_result(self):
        long_text = (
            "We are looking for a Senior Python Developer to join our backend team. "
            "You will design and build scalable microservices, work with PostgreSQL "
            "and Redis, and collaborate with frontend engineers on REST APIs. "
            "Requirements: 5+ years Python, Django or FastAPI, Docker, AWS. "
            "Nice to have: Kubernetes, CI/CD pipelines, Terraform."
        )
        good_result = FetchResult(
            text=long_text,
            title="Backend Engineer",
            company="Acme",
        )
        with patch("app.infrastructure.job_fetcher.fetch_from_url", return_value=good_result):
            result = fetch_job("https://company.com/jobs/123")

        assert result.text == good_result.text
        assert result.requires_manual_input is False
        assert result.title == "Backend Engineer"

    def test_thin_text_returns_requires_manual_input(self):
        thin_result = FetchResult(text="Sign in to see more", title="LinkedIn")
        with patch("app.infrastructure.job_fetcher.fetch_from_url", return_value=thin_result):
            result = fetch_job("https://www.linkedin.com/jobs/view/123")

        assert result.requires_manual_input is True
        assert result.text == ""
        assert result.title == "LinkedIn"

    def test_fetch_error_returns_requires_manual_input(self):
        with patch("app.infrastructure.job_fetcher.fetch_from_url", side_effect=JobFetcherError("timeout")):
            result = fetch_job("https://example.com/jobs/1")

        assert result.requires_manual_input is True
        assert result.text == ""

    def test_empty_text_returns_requires_manual_input(self):
        empty_result = FetchResult(text="")
        with patch("app.infrastructure.job_fetcher.fetch_from_url", return_value=empty_result):
            result = fetch_job("https://example.com/jobs/1")

        assert result.requires_manual_input is True

    def test_metadata_preserved_on_thin_text(self):
        thin_result = FetchResult(text="Sign in", title="SWE at Google", company="Google")
        with patch("app.infrastructure.job_fetcher.fetch_from_url", return_value=thin_result):
            result = fetch_job("https://www.linkedin.com/jobs/view/123")

        assert result.requires_manual_input is True
        assert result.title == "SWE at Google"
        assert result.company == "Google"

    def test_source_url_preserved(self):
        with patch("app.infrastructure.job_fetcher.fetch_from_url", side_effect=JobFetcherError("fail")):
            result = fetch_job("https://example.com/jobs/99")

        assert result.source_url == "https://example.com/jobs/99"
