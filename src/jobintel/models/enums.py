"""Canonical enumerations shared by the database models and Pydantic schemas."""

from __future__ import annotations

import enum


class RemoteClassification(enum.StrEnum):
    REMOTE_WORLDWIDE = "REMOTE_WORLDWIDE"
    REMOTE_ANYWHERE_WITH_MINOR_TIMEZONE_LIMIT = "REMOTE_ANYWHERE_WITH_MINOR_TIMEZONE_LIMIT"
    REMOTE_UK = "REMOTE_UK"
    REMOTE_EUROPE = "REMOTE_EUROPE"
    REMOTE_EMEA = "REMOTE_EMEA"
    REMOTE_APAC = "REMOTE_APAC"
    REMOTE_ASIA = "REMOTE_ASIA"
    REMOTE_MIDDLE_EAST = "REMOTE_MIDDLE_EAST"
    REMOTE_CANADA_ONLY = "REMOTE_CANADA_ONLY"
    REMOTE_US_ONLY = "REMOTE_US_ONLY"
    REMOTE_THAILAND_ONLY = "REMOTE_THAILAND_ONLY"
    REMOTE_SPECIFIC_COUNTRIES = "REMOTE_SPECIFIC_COUNTRIES"
    REMOTE_WITH_OCCASIONAL_TRAVEL = "REMOTE_WITH_OCCASIONAL_TRAVEL"
    HYBRID = "HYBRID"
    ONSITE = "ONSITE"
    UNCLEAR = "UNCLEAR"


class EligibilityStatus(enum.StrEnum):
    YES = "YES"
    NO = "NO"
    UNCLEAR = "UNCLEAR"


class OpportunityClass(enum.StrEnum):
    PERMANENT_EMPLOYMENT = "PERMANENT_EMPLOYMENT"
    FIXED_TERM_CONTRACT = "FIXED_TERM_CONTRACT"
    CONSULTING = "CONSULTING"
    FREELANCE = "FREELANCE"
    SHORT_PROJECT = "SHORT_PROJECT"
    GIG_PROJECT_WORK = "GIG_PROJECT_WORK"
    UNIVERSITY_TEACHING = "UNIVERSITY_TEACHING"
    OTHER = "OTHER"


class EmploymentType(enum.StrEnum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    CONTRACT = "CONTRACT"
    FREELANCE = "FREELANCE"
    INTERNSHIP = "INTERNSHIP"
    UNSPECIFIED = "UNSPECIFIED"


class SeniorityLevel(enum.StrEnum):
    INTERNSHIP = "internship"
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    HEAD = "head"
    PRINCIPAL = "principal"
    EXECUTIVE = "executive"
    UNSPECIFIED = "unspecified"


class CollectionMethod(enum.StrEnum):
    API = "API"
    HTML = "HTML"
    RSS = "RSS"
    SEARCH_DISCOVERY = "SEARCH_DISCOVERY"
    ATS = "ATS"


class Recommendation(enum.StrEnum):
    EXCEPTIONAL_MATCH = "EXCEPTIONAL_MATCH"
    STRONG_APPLY = "STRONG_APPLY"
    WORTH_REVIEWING = "WORTH_REVIEWING"
    STRETCH_OPPORTUNITY = "STRETCH_OPPORTUNITY"
    LOW_PRIORITY = "LOW_PRIORITY"
    IGNORE = "IGNORE"
    INELIGIBLE = "INELIGIBLE"
    EXCLUDED_TRAVEL_REQUIREMENT = "EXCLUDED_TRAVEL_REQUIREMENT"


class ApplicationReadiness(enum.StrEnum):
    READY = "READY"
    READY_WITH_MINOR_CV_TAILORING = "READY_WITH_MINOR_CV_TAILORING"
    NEEDS_TARGETED_COVER_LETTER = "NEEDS_TARGETED_COVER_LETTER"
    NEEDS_MAJOR_REPOSITIONING = "NEEDS_MAJOR_REPOSITIONING"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"


class ApplicationStatus(enum.StrEnum):
    NEW = "New"
    REVIEWING = "Reviewing"
    INTERESTED = "Interested"
    APPLY = "Apply"
    APPLIED = "Applied"
    INTERVIEW = "Interview"
    REJECTED = "Rejected"
    OFFER = "Offer"
    ACCEPTED = "Accepted"
    DECLINED = "Declined"
    NOT_INTERESTED = "Not Interested"
    ARCHIVED = "Archived"


class FeedbackReaction(enum.StrEnum):
    EXCELLENT_MATCH = "EXCELLENT_MATCH"
    RELEVANT = "RELEVANT"
    NOT_INTERESTED = "NOT_INTERESTED"
    NEVER_SHOW_LIKE_THIS = "NEVER_SHOW_LIKE_THIS"


class FeedbackReason(enum.StrEnum):
    WRONG_ROLE = "wrong role"
    TOO_TECHNICAL = "too technical"
    POOR_COMPENSATION = "poor compensation"
    LOCATION_RESTRICTION = "location restriction"
    NOT_ACTUALLY_REMOTE = "not actually remote"
    WRONG_INDUSTRY = "wrong industry"
    TOO_JUNIOR = "too junior"
    TOO_SENIOR = "too senior"
    QUALIFICATION_MISMATCH = "qualification mismatch"
    UNSUITABLE_CONTRACT = "unsuitable contract"
    UNSUITABLE_COMPANY = "unsuitable company"
    OTHER = "other"


class SourceHealthStatus(enum.StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    BROKEN = "BROKEN"
    UNKNOWN = "UNKNOWN"
