"""Versioned salary benchmark data used by the deterministic estimator.

The estimator deliberately keeps benchmark numbers outside the prompt so they
can be reviewed, tested, and updated without changing model instructions.
Figures below are basic monthly salary for permanent roles and exclude AWS,
fixed/variable bonuses, commission, allowances, equity, and benefits.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True)
class RoleBenchmark:
    """One role benchmark within a market."""

    key: str
    label: str
    family: str
    low: Decimal
    median: Decimal
    high: Decimal
    aliases: tuple[str, ...]
    keywords: tuple[str, ...]
    career_track: str = "individual_contributor"


@dataclass(frozen=True)
class SalaryMarket:
    """A versioned set of benchmarks for one country."""

    country: str
    country_code: str
    currency: str
    benchmark_year: int
    compensation_basis: str
    source_name: str
    source_url: str
    macro_reference: str
    roles: Mapping[str, RoleBenchmark]


def _d(value: int | str) -> Decimal:
    return Decimal(str(value))


_MALAYSIA_ROLES = {
    "project_engineer": RoleBenchmark(
        key="project_engineer",
        label="Project Engineer",
        family="project_delivery",
        low=_d(5000),
        median=_d(6500),
        high=_d(8000),
        aliases=(
            "project engineer",
            "implementation engineer",
            "deployment engineer",
        ),
        keywords=(
            "project delivery",
            "implementation",
            "deployment",
            "cutover",
            "handover",
            "project engineer",
        ),
    ),
    "network_engineer": RoleBenchmark(
        key="network_engineer",
        label="Network Engineer",
        family="network_infrastructure",
        low=_d(5500),
        median=_d(11000),
        high=_d(17000),
        aliases=(
            "network engineer",
            "enterprise network engineer",
            "network infrastructure engineer",
            "routing and switching engineer",
            "lan wan engineer",
        ),
        keywords=(
            "network",
            "routing",
            "switching",
            "lan",
            "wan",
            "sd-wan",
            "bgp",
            "ospf",
            "vlan",
        ),
    ),
    "network_security": RoleBenchmark(
        key="network_security",
        label="Network Security Engineer",
        family="cybersecurity",
        low=_d(4000),
        median=_d(8000),
        high=_d(13000),
        aliases=(
            "network security engineer",
            "network security",
            "firewall engineer",
            "security network engineer",
            "sase engineer",
        ),
        keywords=(
            "network security",
            "firewall",
            "palo alto",
            "sase",
            "ipsec",
            "vpn",
            "segmentation",
            "security policy",
        ),
    ),
    "security_engineer": RoleBenchmark(
        key="security_engineer",
        label="Security Engineer / Analyst / SOC Engineer",
        family="cybersecurity",
        low=_d(4000),
        median=_d(8000),
        high=_d(13000),
        aliases=(
            "security engineer",
            "cybersecurity engineer",
            "security analyst",
            "soc engineer",
        ),
        keywords=(
            "cybersecurity",
            "security engineering",
            "soc",
            "incident response",
            "vulnerability",
        ),
    ),
    "security_architect": RoleBenchmark(
        key="security_architect",
        label="Security Architect",
        family="cybersecurity",
        low=_d(15000),
        median=_d(22000),
        high=_d(30000),
        aliases=("security architect", "cybersecurity architect"),
        keywords=(
            "security architecture",
            "enterprise security architecture",
            "security strategy",
            "reference architecture",
        ),
    ),
    "cloud_security": RoleBenchmark(
        key="cloud_security",
        label="Cloud Security / DevSecOps / Application Security",
        family="cybersecurity",
        low=_d(8000),
        median=_d(16000),
        high=_d(25000),
        aliases=(
            "cloud security engineer",
            "devsecops engineer",
            "application security engineer",
        ),
        keywords=("cloud security", "devsecops", "application security"),
    ),
    "technical_support": RoleBenchmark(
        key="technical_support",
        label="Technical Support / Helpdesk / Desktop Support",
        family="technical_support",
        low=_d(3500),
        median=_d(7500),
        high=_d(12000),
        aliases=(
            "technical support engineer",
            "it support engineer",
            "network support engineer",
            "helpdesk engineer",
            "desktop support engineer",
        ),
        keywords=(
            "technical support",
            "troubleshooting",
            "helpdesk",
            "service desk",
            "incident resolution",
            "network support",
        ),
    ),
    "cloud_engineer": RoleBenchmark(
        key="cloud_engineer",
        label="Cloud Engineer",
        family="cloud_infrastructure",
        low=_d(4000),
        median=_d(6000),
        high=_d(9000),
        aliases=("cloud engineer", "cloud operations engineer"),
        keywords=("cloud operations", "aws", "azure", "gcp", "cloud engineer"),
    ),
    "senior_cloud_engineer": RoleBenchmark(
        key="senior_cloud_engineer",
        label="Senior Cloud Engineer",
        family="cloud_infrastructure",
        low=_d(9000),
        median=_d(12000),
        high=_d(15000),
        aliases=("senior cloud engineer",),
        keywords=("senior cloud", "cloud architecture", "cloud operations"),
    ),
    "devops_engineer": RoleBenchmark(
        key="devops_engineer",
        label="DevOps Engineer / SRE",
        family="devops",
        low=_d(4000),
        median=_d(8000),
        high=_d(12000),
        aliases=("devops engineer", "site reliability engineer", "sre"),
        keywords=("devops", "sre", "ci/cd", "automation", "kubernetes"),
    ),
    "senior_devops_engineer": RoleBenchmark(
        key="senior_devops_engineer",
        label="Senior DevOps Engineer / SRE",
        family="devops",
        low=_d(12000),
        median=_d(16000),
        high=_d(20000),
        aliases=("senior devops engineer", "senior site reliability engineer"),
        keywords=("senior devops", "platform engineering", "sre"),
    ),
    "infrastructure_architect": RoleBenchmark(
        key="infrastructure_architect",
        label="Infrastructure Architect",
        family="network_infrastructure",
        low=_d(15000),
        median=_d(22000),
        high=_d(30000),
        aliases=("infrastructure architect", "it infrastructure architect"),
        keywords=("infrastructure architecture", "enterprise infrastructure"),
    ),
    "network_architect": RoleBenchmark(
        key="network_architect",
        label="Network Architect",
        family="network_infrastructure",
        low=_d(15000),
        median=_d(25000),
        high=_d(35000),
        aliases=("network architect", "enterprise network architect"),
        keywords=("network architecture", "enterprise architecture", "design authority"),
    ),
    "technical_project_manager": RoleBenchmark(
        key="technical_project_manager",
        label="Technical Project Manager",
        family="project_delivery",
        low=_d(11000),
        median=_d(22000),
        high=_d(35000),
        aliases=(
            "technical project manager",
            "it project manager",
            "infrastructure project manager",
            "network project manager",
        ),
        keywords=(
            "project management",
            "program management",
            "budget ownership",
            "portfolio",
            "project manager",
            "governance",
        ),
        career_track="management",
    ),
    "project_manager": RoleBenchmark(
        key="project_manager",
        label="Project Manager",
        family="project_delivery",
        low=_d(11000),
        median=_d(22000),
        high=_d(35000),
        aliases=("project manager",),
        keywords=("project management", "project manager", "budget", "portfolio"),
        career_track="management",
    ),
    "project_coordinator": RoleBenchmark(
        key="project_coordinator",
        label="Project Analyst / Project Coordinator",
        family="project_delivery",
        low=_d(3000),
        median=_d(4500),
        high=_d(6000),
        aliases=("project coordinator", "project analyst", "project administrator"),
        keywords=("project coordination", "project tracking", "project support"),
    ),
    "service_delivery_manager": RoleBenchmark(
        key="service_delivery_manager",
        label="Service Delivery / Technical Delivery Manager",
        family="project_delivery",
        low=_d(13000),
        median=_d(19000),
        high=_d(25000),
        aliases=("service delivery manager", "technical delivery manager", "it delivery manager"),
        keywords=("service delivery", "technical delivery", "sla management", "vendor management"),
        career_track="management",
    ),
    "solution_architect": RoleBenchmark(
        key="solution_architect",
        label="Solution Architect",
        family="architecture",
        low=_d(15000),
        median=_d(25000),
        high=_d(35000),
        aliases=("solution architect", "solutions architect"),
        keywords=("solution architecture", "architecture design", "technical design authority"),
    ),
    "software_engineer": RoleBenchmark(
        key="software_engineer",
        label="Software Engineer",
        family="software_engineering",
        low=_d(3500),
        median=_d(10000),
        high=_d(17000),
        aliases=(
            "software engineer",
            "backend engineer",
            "frontend engineer",
            "full stack engineer",
            "software developer",
        ),
        keywords=("software engineering", "backend", "frontend", "full stack", "developer"),
    ),
    "tech_lead": RoleBenchmark(
        key="tech_lead",
        label="Technology Lead",
        family="software_engineering",
        low=_d(10000),
        median=_d(17000),
        high=_d(25000),
        aliases=("tech lead", "technical lead", "engineering lead"),
        keywords=("technical leadership", "tech lead", "engineering leadership"),
    ),
    "business_analyst": RoleBenchmark(
        key="business_analyst",
        label="Business Analyst",
        family="business_analysis",
        low=_d(4000),
        median=_d(6500),
        high=_d(9000),
        aliases=("business analyst",),
        keywords=("business analysis", "requirements gathering", "process analysis"),
    ),
    "technical_business_analyst": RoleBenchmark(
        key="technical_business_analyst",
        label="Technical Business / Systems / Solutions Analyst",
        family="business_analysis",
        low=_d(5000),
        median=_d(8500),
        high=_d(12000),
        aliases=("technical business analyst", "systems analyst", "solutions analyst"),
        keywords=("technical analysis", "systems analysis", "solution analysis"),
    ),
}


MALAYSIA_MARKET_2025 = SalaryMarket(
    country="Malaysia",
    country_code="MY",
    currency="MYR",
    benchmark_year=2025,
    compensation_basis=(
        "Basic monthly salary for a permanent role; excludes AWS, fixed or "
        "variable bonus, commission, allowances, equity, and benefits."
    ),
    source_name="Randstad Malaysia 2025 Job Market Outlook & Salary Guide",
    source_url=(
        "https://www.randstad.com.my/s3fs-media/my/public/2024-12/"
        "randstad-malaysia-2025-job-market-outlook-and-salary-guide.pdf"
    ),
    macro_reference=(
        "Malaysia formal-sector median monthly wage: MYR 3,167 in December "
        "2025 (DOSM). Used only as a broad sanity check."
    ),
    roles=_MALAYSIA_ROLES,
)


MARKETS_BY_COUNTRY_CODE: Mapping[str, SalaryMarket] = {
    MALAYSIA_MARKET_2025.country_code: MALAYSIA_MARKET_2025,
}
