from dataclasses import dataclass, field
from typing import Optional
from datetime import date


@dataclass
class Feed:
    source_file: str
    onix_version: str  # '2.1', '3.0', '3.1'
    sender_name: Optional[str]
    sender_email: Optional[str]
    sent_at: Optional[str]  # ISO datetime string or None
    source_type: str  # 'file' | 'url' | 'upload'


@dataclass
class Contributor:
    sequence_number: Optional[int]
    role_code: str
    role: str
    names_before_key: Optional[str]
    key_names: Optional[str]
    display_name: Optional[str]
    inverted_name: Optional[str]
    from_language_code: Optional[str]
    biographical_note: Optional[str]
    bio_textformat: Optional[str]
    contributor_id_type: Optional[str]
    contributor_id_value: Optional[str]


@dataclass
class Subject:
    is_main_subject: bool
    scheme_code: str
    scheme_name: Optional[str]
    scheme_version: Optional[str]
    subject_code: Optional[str]
    subject_heading_text: Optional[str]


@dataclass
class Price:
    supplier_name: Optional[str]
    supplier_role_code: Optional[str]
    availability_code: Optional[str]
    availability: Optional[str]
    price_type_code: Optional[str]
    price_status_code: Optional[str]
    price_amount: Optional[float]
    currency_code: Optional[str]
    countries_included: Optional[str]
    countries_excluded: Optional[str]
    regions_included: Optional[str]
    discount_code_type_code: Optional[str]
    discount_code: Optional[str]
    discount_percent: Optional[float]
    tax_type_code: Optional[str]
    tax_rate_code: Optional[str]
    tax_rate_percent: Optional[float]
    taxable_amount: Optional[float]
    tax_amount: Optional[float]
    market_reference: Optional[str]
    market_publishing_status_code: Optional[str]
    market_date: Optional[date]


@dataclass
class Book:
    record_reference: str
    notification_type_code: Optional[str] = None
    isbn13: Optional[str] = None
    isbn10: Optional[str] = None
    gtin13: Optional[str] = None
    identifiers: list = field(default_factory=list)
    title: Optional[str] = None
    subtitle: Optional[str] = None
    full_title: Optional[str] = None
    series_name: Optional[str] = None
    series_number: Optional[str] = None
    product_form_code: Optional[str] = None
    product_form: Optional[str] = None
    edition_number: Optional[int] = None
    edition_statement: Optional[str] = None
    no_edition: bool = False
    publisher_name: Optional[str] = None
    imprint_name: Optional[str] = None
    city_of_publication: Optional[str] = None
    country_of_publication: Optional[str] = None
    country_of_manufacture: Optional[str] = None
    publishing_status_code: Optional[str] = None
    publishing_status: Optional[str] = None
    publication_date: Optional[date] = None
    availability_code: Optional[str] = None
    availability: Optional[str] = None
    page_count: Optional[int] = None
    height_mm: Optional[float] = None
    width_mm: Optional[float] = None
    thickness_mm: Optional[float] = None
    weight_g: Optional[float] = None
    cover_url: Optional[str] = None
    short_description: Optional[str] = None
    description: Optional[str] = None
    language_code: Optional[str] = None
    original_language_code: Optional[str] = None
    audience_code: Optional[str] = None
    trade_category_code: Optional[str] = None
    rights_countries_included: Optional[str] = None
    rights_countries_excluded: Optional[str] = None
    rights_regions: Optional[str] = None
    languages: list = field(default_factory=list)
    texts: list = field(default_factory=list)
    media: list = field(default_factory=list)
    related: list = field(default_factory=list)
    contributors: list = field(default_factory=list)  # list[Contributor]
    subjects: list = field(default_factory=list)  # list[Subject]
    prices: list = field(default_factory=list)  # list[Price]
    blocks_present: list = field(default_factory=list)  # e.g. ['DescriptiveDetail', 'ProductSupply']
