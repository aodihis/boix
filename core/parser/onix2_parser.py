"""ONIX 2.1 parser — same output shape as onix_parser.py but for ONIX 2.1 element names."""
import os
from datetime import date
from typing import Optional

from lxml import etree

from parser.codelists import code_to_label
from parser.models import Book, Contributor, Feed, Price, Subject
from parser.shorttags import normalize_elem_tree, normalize_tag


def _child_text(elem: etree._Element, tag: str) -> Optional[str]:
    child = elem.find(tag)
    if child is not None and child.text:
        return child.text.strip() or None
    return None


def _parse_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    raw = raw.strip()
    if len(raw) == 8:
        try:
            return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
        except ValueError:
            return None
    if len(raw) == 4:
        try:
            return date(int(raw), 1, 1)
        except ValueError:
            return None
    return None


def _parse_contributors2(product: etree._Element) -> list[Contributor]:
    contributors = []
    for contrib in product.findall("Contributor"):
        seq_text = _child_text(contrib, "SequenceNumber")
        sequence_number = int(seq_text) if seq_text else None
        role_code = _child_text(contrib, "ContributorRole") or ""
        role = code_to_label("contributor_role", role_code)

        bio_elem = contrib.find("BiographicalNote")
        bio_text = None
        bio_fmt = None
        if bio_elem is not None:
            bio_text = etree.tostring(bio_elem, encoding="unicode", method="text").strip() or None
            bio_fmt = bio_elem.get("textformat")

        # Contributor ID — ONIX 2.1 uses PersonNameIdentifier
        id_type = None
        id_value = None
        for pni in contrib.findall("PersonNameIdentifier"):
            id_type = _child_text(pni, "PersonNameIDType")
            id_value = _child_text(pni, "IDValue")
            if id_value:
                break

        contributors.append(
            Contributor(
                sequence_number=sequence_number,
                role_code=role_code,
                role=role,
                names_before_key=_child_text(contrib, "NamesBeforeKey"),
                key_names=_child_text(contrib, "KeyNames"),
                display_name=_child_text(contrib, "PersonName"),
                inverted_name=_child_text(contrib, "PersonNameInverted"),
                from_language_code=_child_text(contrib, "FromLanguage"),
                biographical_note=bio_text,
                bio_textformat=bio_fmt,
                contributor_id_type=id_type,
                contributor_id_value=id_value,
            )
        )
    return contributors


def _parse_subjects2(product: etree._Element) -> list[Subject]:
    subjects = []

    # BASICMainSubject — BISAC main subject code
    main_subj = _child_text(product, "BASICMainSubject")
    if main_subj:
        subjects.append(
            Subject(
                is_main_subject=True,
                scheme_code="10",
                scheme_name="BISAC",
                scheme_version=None,
                subject_code=main_subj,
                subject_heading_text=None,
            )
        )

    # Subject elements
    for subj in product.findall("Subject"):
        scheme_code = _child_text(subj, "SubjectSchemeIdentifier") or ""
        subjects.append(
            Subject(
                is_main_subject=False,
                scheme_code=scheme_code,
                scheme_name=code_to_label("subject_scheme", scheme_code) if scheme_code else None,
                scheme_version=_child_text(subj, "SubjectSchemeVersion"),
                subject_code=_child_text(subj, "SubjectCode"),
                subject_heading_text=_child_text(subj, "SubjectHeadingText"),
            )
        )

    return subjects


def _parse_supply_detail2(product: etree._Element) -> list[Price]:
    prices = []
    for sd in product.findall("SupplyDetail"):
        supplier_name = _child_text(sd, "SupplierName")
        supplier_role_code = _child_text(sd, "SupplierRole")
        avail_code = _child_text(sd, "ProductAvailability")
        availability = code_to_label("availability", avail_code) if avail_code else None

        for price_elem in sd.findall("Price"):
            price_type_code = _child_text(price_elem, "PriceTypeCode")
            price_status_code = _child_text(price_elem, "PriceStatus")
            amount_str = _child_text(price_elem, "PriceAmount")
            price_amount = float(amount_str) if amount_str else None
            currency_code = _child_text(price_elem, "CurrencyCode")

            countries_included = _child_text(price_elem, "CountryIncluded")
            countries_excluded = _child_text(price_elem, "CountryExcluded")
            regions_included = None

            disc_type = _child_text(price_elem, "DiscountCodeType")
            disc_code = _child_text(price_elem, "DiscountCode")
            disc_pct_str = _child_text(price_elem, "DiscountPercent")
            discount_percent = float(disc_pct_str) if disc_pct_str else None

            tax_type = _child_text(price_elem, "TaxRateCode1")
            tax_rate_code = _child_text(price_elem, "TaxRateCode1")
            tax_pct_str = _child_text(price_elem, "TaxRatePercent1")
            tax_rate_pct = float(tax_pct_str) if tax_pct_str else None
            ta_str = _child_text(price_elem, "TaxableAmount1")
            taxable_amt = float(ta_str) if ta_str else None
            t_str = _child_text(price_elem, "TaxAmount1")
            tax_amt = float(t_str) if t_str else None

            prices.append(
                Price(
                    supplier_name=supplier_name,
                    supplier_role_code=supplier_role_code,
                    availability_code=avail_code,
                    availability=availability,
                    price_type_code=price_type_code,
                    price_status_code=price_status_code,
                    price_amount=price_amount,
                    currency_code=currency_code,
                    countries_included=countries_included,
                    countries_excluded=countries_excluded,
                    regions_included=regions_included,
                    discount_code_type_code=disc_type,
                    discount_code=disc_code,
                    discount_percent=discount_percent,
                    tax_type_code=tax_type,
                    tax_rate_code=tax_rate_code,
                    tax_rate_percent=tax_rate_pct,
                    taxable_amount=taxable_amt,
                    tax_amount=tax_amt,
                    market_reference=None,
                    market_publishing_status_code=None,
                    market_date=None,
                )
            )
    return prices


def _parse_product2(product: etree._Element) -> Book:
    record_ref = _child_text(product, "RecordReference") or ""
    notif_code = _child_text(product, "NotificationType")

    book = Book(
        record_reference=record_ref,
        notification_type_code=notif_code,
    )

    # Product identifiers
    identifiers = []
    for pi in product.findall("ProductIdentifier"):
        id_type = _child_text(pi, "ProductIDType")
        id_value = _child_text(pi, "IDValue")
        if id_type == "03":
            book.gtin13 = id_value
        elif id_type == "15":
            book.isbn13 = id_value
        elif id_type == "02":
            book.isbn10 = id_value
        else:
            identifiers.append({"id_type_code": id_type, "id_value": id_value})
    book.identifiers = identifiers

    # Title — ONIX 2.1 uses <Title><TitleType>01<TitleText>
    for title_elem in product.findall("Title"):
        title_type = _child_text(title_elem, "TitleType")
        if title_type == "01" or title_type is None:
            book.title = _child_text(title_elem, "TitleText")
            book.subtitle = _child_text(title_elem, "Subtitle")
            if book.title and book.subtitle:
                book.full_title = f"{book.title}: {book.subtitle}"
            else:
                book.full_title = book.title or book.subtitle
            break

    # Series
    series_elem = product.find("Series")
    if series_elem is not None:
        book.series_name = _child_text(series_elem, "TitleOfSeries")
        book.series_number = _child_text(series_elem, "NumberWithinSeries")

    # Product form
    book.product_form_code = _child_text(product, "ProductForm")
    if book.product_form_code:
        book.product_form = code_to_label("product_form", book.product_form_code)

    # Edition
    ed_num = _child_text(product, "EditionNumber")
    book.edition_number = int(ed_num) if ed_num else None
    book.edition_statement = _child_text(product, "EditionStatement")

    # Page count
    pages = _child_text(product, "NumberOfPages")
    book.page_count = int(pages) if pages else None

    # Language
    lang_elem = product.find("Language")
    if lang_elem is not None:
        role = _child_text(lang_elem, "LanguageRole")
        code = _child_text(lang_elem, "LanguageCode")
        if role == "01":
            book.language_code = code
        elif role == "02":
            book.original_language_code = code
        book.languages = [{"language_role_code": role, "language_code": code}] if role and code else []

    # Publisher / imprint
    publisher_elem = product.find("Publisher")
    if publisher_elem is not None:
        book.publisher_name = _child_text(publisher_elem, "PublisherName")

    book.imprint_name = _child_text(product, "ImprintName")
    book.city_of_publication = _child_text(product, "CityOfPublication")
    book.country_of_publication = _child_text(product, "CountryOfPublication")

    status_code = _child_text(product, "PublishingStatus")
    book.publishing_status_code = status_code
    if status_code:
        book.publishing_status = code_to_label("publishing_status", status_code)

    # Publication date
    book.publication_date = _parse_date(_child_text(product, "PublicationDate"))

    # Audience
    book.audience_code = _child_text(product, "AudienceCode")

    # Rights
    sales_rights = product.find("SalesRights")
    if sales_rights is not None:
        book.rights_countries_included = _child_text(sales_rights, "RightsCountry")
        book.rights_regions = _child_text(sales_rights, "RightsTerritory")

    # Texts
    texts = []
    otc = _child_text(product, "OtherText")
    if otc:
        texts.append({"text_type_code": "03", "text_value": otc, "textformat": None, "source_title": None})
        book.description = otc
    book.texts = texts

    # Media from MediaFile
    media = []
    for mf in product.findall("MediaFile"):
        link = _child_text(mf, "MediaFileLink")
        media_type = _child_text(mf, "MediaFileTypeCode")
        if link:
            media.append({"resource_type_code": media_type, "resource_link": link})
            # Media type 04 = front cover image
            if media_type == "04" and not book.cover_url:
                book.cover_url = link
    book.media = media

    book.contributors = _parse_contributors2(product)
    book.subjects = _parse_subjects2(product)

    prices = _parse_supply_detail2(product)
    book.prices = prices
    if prices:
        book.availability_code = prices[0].availability_code
        book.availability = prices[0].availability

    # ONIX 2.1 has no block update concept — blocks_present stays empty
    return book


def parse_onix2(file_path: str) -> tuple[Feed, list[Book]]:
    """Parses ONIX 2.1 file. No namespace. Always treats records as full replacements."""
    books: list[Book] = []
    feed_meta: dict = {}

    context = etree.iterparse(file_path, events=("end",), recover=True)

    for event, elem in context:
        tag = normalize_tag(elem.tag) if isinstance(elem.tag, str) else ""

        if tag == "Header":
            normalize_elem_tree(elem)
            sender = elem.find("Sender")
            if sender is not None:
                feed_meta["sender_name"] = _child_text(sender, "SenderName")
                feed_meta["sender_email"] = _child_text(sender, "EmailAddress")
            else:
                # Reference format uses FromCompany/FromEmail; short tags normalize to SenderName/EmailAddress
                feed_meta["sender_name"] = _child_text(elem, "FromCompany") or _child_text(elem, "SenderName")
                feed_meta["sender_email"] = _child_text(elem, "FromEmail") or _child_text(elem, "EmailAddress")
            sent = _child_text(elem, "SentDate") or _child_text(elem, "SentDateTime")
            feed_meta["sent_at"] = sent
            elem.clear()
            continue

        if tag == "Product":
            normalize_elem_tree(elem)
            book = _parse_product2(elem)
            books.append(book)
            elem.clear()
            continue

    from parser.detect import detect_onix_version

    version = detect_onix_version(file_path)
    feed = Feed(
        source_file=os.path.basename(file_path),
        onix_version=version,
        sender_name=feed_meta.get("sender_name"),
        sender_email=feed_meta.get("sender_email"),
        sent_at=feed_meta.get("sent_at"),
        source_type="file",
    )

    return feed, books
