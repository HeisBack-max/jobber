"""Synthetic job posting fixtures covering every scenario required by
the spec's testing section (§58). Each fixture is (location_raw,
description_text) unless noted, mirroring real-world phrasing patterns.
"""

from __future__ import annotations

PERFECT_WORLDWIDE_AI_TRAINER = (
    "Remote - Worldwide",
    """We are hiring a Generative AI Trainer to deliver enterprise AI adoption
    training. This is a remote worldwide position - work from anywhere.
    You will design curriculum, deliver workshops, and support customer
    enablement for our generative AI platform. Prompt engineering and
    instructional design experience required.""",
)

US_ONLY_REMOTE_CYBERSECURITY_TRAINER = (
    "Remote - United States",
    """Remote - United States only. Candidates must reside in the United
    States. Deliver cybersecurity awareness training to enterprise clients.
    Must be a US citizen due to government contract requirements.""",
)

THAILAND_RESIDENT_ONLY_AI_ROLE = (
    "Remote - Thailand",
    """Remote (Thailand) - AI Curriculum Developer. Thailand residents only.
    Must reside in Thailand. Bangkok office available but not required.""",
)

HYBRID_AI_ROLE_LONDON = (
    "London, UK",
    """Hybrid AI Enablement Consultant based in our London office. This is a
    hybrid role - 3 days a week in the office. You will train enterprise
    customers on generative AI adoption.""",
)

IRRELEVANT_SOFTWARE_ENGINEER = (
    "Remote - Worldwide",
    """Senior Backend Software Engineer. Remote worldwide. 8+ years of
    full-time production software engineering experience required. Deep
    Kubernetes and distributed systems experience mandatory. Must have
    shipped large-scale production Go or Rust services.""",
)

STRONG_AI_SECURITY_OPPORTUNITY = (
    "Remote - EMEA",
    """AI Security Enablement Lead - Remote EMEA. You will lead LLM red-team
    exercises, stress-test jailbreak resilience, and deliver cybersecurity
    and AI security training to enterprise customers across EMEA. Strong
    background in adversarial LLM testing and technical instruction
    required.""",
)

REMOTE_UNIVERSITY_CYBERSECURITY_INSTRUCTOR = (
    "Remote - Worldwide",
    """Online Faculty - Cybersecurity. Remote worldwide, fully distributed
    teaching team. Deliver online cybersecurity instruction, OSINT and
    GRC modules to a global student cohort.""",
)

MISLEADING_REMOTE_ADVERTISEMENT = (
    "Remote (US)",
    """Remote (US) - AI Trainer. This role is based in the United States.
    Applicants must reside in one of the 48 contiguous United States.""",
)

ANTHROPIC_STYLE_REMOTE_FRIENDLY_TRAVEL_REQUIRED = (
    "Remote-Friendly (Travel-Required)",
    """This role is Remote-Friendly (Travel-Required). Some travel may be
    required to collaborate with the team in person. Specific residency
    and travel expectations vary by role.""",
)

OPENAI_LONDON_OPPORTUNITY = (
    "London, UK",
    """Technical Trainer, based in our London office. This role requires
    five days a week in the office to collaborate with the London-based
    team. On-site collaboration is a core part of this role.""",
)

US_STARTUP_HIRING_WORLDWIDE = (
    "Remote - Worldwide",
    """(San Francisco-headquartered startup) AI Enablement Specialist -
    remote worldwide, work from anywhere. We hire globally and support
    distributed teams across every timezone.""",
)

THAI_STARTUP_HIRING_WORLDWIDE = (
    "Remote - Worldwide",
    """(Bangkok-headquartered startup) Generative AI Trainer - remote
    worldwide, fully distributed team, work from anywhere in the world.""",
)

STRONG_VERTEX_AI_CONSULTANT_ROLE = (
    "Remote - UK/EMEA",
    """Vertex AI Enablement Consultant - Remote UK/EMEA. Train enterprise
    customers on Google Cloud generative AI adoption using Vertex AI and
    Gemini. Strong technical training and client consulting background
    required.""",
)

LOW_PAID_GENERIC_ANNOTATION_GIG = (
    "Remote - Worldwide",
    """Data Annotation Contributor - remote worldwide. Label images and
    text for machine learning datasets. $3-5/hour. No specialist
    background required.""",
)

HIGH_VALUE_SPECIALIST_AI_EVALUATION_GIG = (
    "Remote - International",
    """LLM Security Evaluation Specialist - international remote, work from
    anywhere. $65-90/hour, 10-20 hours/week. Adversarial testing and
    prompt-injection evaluation of enterprise LLM deployments.""",
)

REGULAR_US_TRAVEL_REQUIRED = (
    "Remote - Worldwide",
    """Remote worldwide role. Monthly travel to the United States is
    required to attend team offsites in our San Francisco office.""",
)

REGULAR_THAILAND_TRAVEL_REQUIRED = (
    "Remote - APAC",
    """Remote APAC role. Quarterly travel to Thailand is required to
    attend regional offsites in our Bangkok office.""",
)

OCCASIONAL_INTERNATIONAL_TRAVEL = (
    "Remote - Worldwide",
    """Remote worldwide role, work from anywhere. Occasional travel
    (roughly once a year) to an international conference may be
    required.""",
)
