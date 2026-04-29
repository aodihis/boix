import json
import re
from datetime import date
from typing import Optional

from lxml import etree

from parser.codelists import code_to_label
from parser.models import Book, Contributor, Feed, Price, Subject
from parser.shorttags import normalize_tag


def _strip_ns(tag: object) -> str:
    """Strips Clark-notation namespace and normalizes ONIX short tags to reference names.
    lxml comment/PI nodes have callable tags — treat those as empty."""
    if not isinstance(tag, str):
        return ""
    local = tag.split("}", 1)[1] if tag and tag[0] == "{" else tag
    return normalize_tag(local)


def _detect_ns(root: etree._Element) -> str:
    """Returns namespace URI if present, empty string otherwise."""
    tag = root.tag
    if not isinstance(tag, str):
        return ""
    if tag[0] == "{":
        return tag.split("}", 1)[0][1:]
    return ""


def _child_text(elem: etree._Element, local_name: str, ns: str) -> Optional[str]:
    """Returns text of first matching child by local name, ignoring namespace."""
    for child in elem:
        if _strip_ns(child.tag) == local_name:
            return (child.text or "").strip() or None
    return None


def _all_children(elem: etree._Element, local_name: str) -> list[etree._Element]:
    """Returns all direct children matching local name."""
    return [c for c in elem if _strip_ns(c.tag) == local_name]


def _parse_date(raw: Optional[str]) -> Optional[date]:
    """Parses YYYYMMDD or YYYY date strings into date objects."""
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


def _parse_header(header_elem: etree._Element) -> dict:
    """Extracts sender/date fields from Header element."""
    sender = None
    for child in header_elem:
        if _strip_ns(child.tag) == "Sender":
            sender = child
            break

    sender_name = _child_text(sender, "SenderName", "") if sender is not None else None
    sender_email = _child_text(sender, "EmailAddress", "") if sender is not None else None
    sent_at_raw = _child_text(header_elem, "SentDateTime", "")

    return {
        "sender_name": sender_name,
        "sender_email": sender_email,
        "sent_at": sent_at_raw,
    }


def _parse_contributors(descriptive: etree._Element) -> list[Contributor]:
    contributors = []
    for contrib_elem in _all_children(descriptive, "Contributor"):
        seq_text = _child_text(contrib_elem, "SequenceNumber", "")
        sequence_number = int(seq_text) if seq_text else None
        role_code = _child_text(contrib_elem, "ContributorRole", "") or ""
        role = code_to_label("contributor_role", role_code)

        # Contributor identifier — take first NameIdentifier that has an IDValue
        id_type = None
        id_value = None
        for ni in _all_children(contrib_elem, "NameIdentifier"):
            id_type = _child_text(ni, "NameIDType", "")
            id_value = _child_text(ni, "IDValue", "")
            if id_value:
                break

        bio_elem = None
        for child in contrib_elem:
            if _strip_ns(child.tag) == "BiographicalNote":
                bio_elem = child
                break

        bio_text = None
        bio_fmt = None
        if bio_elem is not None:
            # Preserve inner XML as text
            bio_text = etree.tostring(bio_elem, encoding="unicode", method="text").strip() or None
            bio_fmt = bio_elem.get("textformat")

        from_lang = _child_text(contrib_elem, "FromLanguage", "")

        contributors.append(
            Contributor(
                sequence_number=sequence_number,
                role_code=role_code,
                role=role,
                names_before_key=_child_text(contrib_elem, "NamesBeforeKey", ""),
                key_names=_child_text(contrib_elem, "KeyNames", ""),
                display_name=_child_text(contrib_elem, "DisplayName", ""),
                inverted_name=_child_text(contrib_elem, "PersonNameInverted", ""),
                from_language_code=from_lang,
                biographical_note=bio_text,
                bio_textformat=bio_fmt,
                contributor_id_type=id_type,
                contributor_id_value=id_value,
            )
        )
    return contributors


def _parse_subjects(descriptive: etree._Element) -> list[Subject]:
    subjects = []
    for subj_elem in _all_children(descriptive, "Subject"):
        is_main = any(_strip_ns(c.tag) == "MainSubject" for c in subj_elem)
        scheme_code = _child_text(subj_elem, "SubjectSchemeIdentifier", "") or ""
        scheme_name = code_to_label("subject_scheme", scheme_code) if scheme_code else None
        subjects.append(
            Subject(
                is_main_subject=is_main,
                scheme_code=scheme_code,
                scheme_name=scheme_name,
                scheme_version=_child_text(subj_elem, "SubjectSchemeVersion", ""),
                subject_code=_child_text(subj_elem, "SubjectCode", ""),
                subject_heading_text=_child_text(subj_elem, "SubjectHeadingText", ""),
            )
        )
    return subjects


def _parse_languages(descriptive: etree._Element) -> tuple[list[dict], Optional[str], Optional[str]]:
    """Returns (languages_jsonb, primary_language_code, original_language_code)."""
    languages = []
    lang_code = None
    orig_lang_code = None
    for lang_elem in _all_children(descriptive, "Language"):
        role = _child_text(lang_elem, "LanguageRole", "")
        code = _child_text(lang_elem, "LanguageCode", "")
        if role and code:
            languages.append({"language_role_code": role, "language_code": code})
            if role == "01":
                lang_code = code
            elif role == "02":
                orig_lang_code = code
    return languages, lang_code, orig_lang_code


def _parse_measures(descriptive: etree._Element) -> dict:
    result: dict = {}
    for m in _all_children(descriptive, "Measure"):
        m_type = _child_text(m, "MeasureType", "")
        m_val = _child_text(m, "Measurement", "")
        unit = _child_text(m, "MeasureUnitCode", "") or ""
        if not m_type or not m_val:
            continue
        try:
            val = float(m_val)
        except ValueError:
            continue
        # Convert to mm/g: unit 'cm' → *10, 'in' → *25.4, 'oz' → *28.35
        if unit == "cm":
            val = val * 10
        elif unit == "in":
            val = val * 25.4
        elif unit == "oz":
            val = val * 28.35
        # MeasureType: 01=height, 02=width, 03=thickness, 08=weight
        if m_type == "01":
            result["height_mm"] = val
        elif m_type == "02":
            result["width_mm"] = val
        elif m_type == "03":
            result["thickness_mm"] = val
        elif m_type == "08":
            result["weight_g"] = val
    return result


def _parse_descriptive_detail(dd: etree._Element, book: Book) -> None:
    book.blocks_present.append("DescriptiveDetail")

    book.product_form_code = _child_text(dd, "ProductForm", "")
    if book.product_form_code:
        book.product_form = code_to_label("product_form", book.product_form_code)

    # No-edition flag
    book.no_edition = any(_strip_ns(c.tag) == "NoEdition" for c in dd)

    # Edition
    ed_num = _child_text(dd, "EditionNumber", "")
    book.edition_number = int(ed_num) if ed_num else None
    book.edition_statement = _child_text(dd, "EditionStatement", "")

    # Country of manufacture
    book.country_of_manufacture = _child_text(dd, "CountryOfManufacture", "")

    # Audience
    for aud_elem in _all_children(dd, "Audience"):
        code_type = _child_text(aud_elem, "AudienceCodeType", "")
        if code_type == "01":
            book.audience_code = _child_text(aud_elem, "AudienceCodeValue", "")
            break

    # Title — TitleType 01 = distinctive title
    for td in _all_children(dd, "TitleDetail"):
        title_type = _child_text(td, "TitleType", "")
        for te in _all_children(td, "TitleElement"):
            level = _child_text(te, "TitleElementLevel", "")
            if title_type == "01" and level == "01":
                without_prefix = _child_text(te, "TitleWithoutPrefix", "")
                prefix = _child_text(te, "TitlePrefix", "")
                book.title = f"{prefix} {without_prefix}".strip() if prefix else without_prefix
                book.subtitle = _child_text(te, "Subtitle", "")
                if book.title and book.subtitle:
                    book.full_title = f"{book.title}: {book.subtitle}"
                else:
                    book.full_title = book.title or book.subtitle

    # Series from Collection (CollectionType 10 = publisher series)
    for coll in _all_children(dd, "Collection"):
        for ctd in _all_children(coll, "TitleDetail"):
            for cte in _all_children(ctd, "TitleElement"):
                level = _child_text(cte, "TitleElementLevel", "")
                if level == "02":
                    prefix = _child_text(cte, "TitlePrefix", "")
                    without = _child_text(cte, "TitleWithoutPrefix", "")
                    book.series_name = f"{prefix} {without}".strip() if prefix else without
                elif level == "01":
                    book.series_number = _child_text(cte, "PartNumber", "")

    # Extent — ExtentType 00=pages (main)
    for ext in _all_children(dd, "Extent"):
        ext_type = _child_text(ext, "ExtentType", "")
        if ext_type == "00":
            val = _child_text(ext, "ExtentValue", "")
            if val:
                try:
                    book.page_count = int(val)
                except ValueError:
                    pass

    measures = _parse_measures(dd)
    book.height_mm = measures.get("height_mm")
    book.width_mm = measures.get("width_mm")
    book.thickness_mm = measures.get("thickness_mm")
    book.weight_g = measures.get("weight_g")

    book.contributors = _parse_contributors(dd)
    book.subjects = _parse_subjects(dd)
    languages, lang_code, orig_lang_code = _parse_languages(dd)
    book.languages = languages
    book.language_code = lang_code
    book.original_language_code = orig_lang_code


def _parse_collateral_detail(cd: etree._Element, book: Book) -> None:
    book.blocks_present.append("CollateralDetail")
    texts = []
    media = []

    for tc in _all_children(cd, "TextContent"):
        text_type = _child_text(tc, "TextType", "")
        text_elem = None
        for child in tc:
            if _strip_ns(child.tag) == "Text":
                text_elem = child
                break
        if text_elem is None:
            continue
        raw_text = etree.tostring(text_elem, encoding="unicode", method="text").strip()
        fmt = text_elem.get("textformat")
        source_title = _child_text(tc, "SourceTitle", "")
        content_audience_code = _child_text(tc, "ContentAudience", "")
        texts.append(
            {
                "text_type_code": text_type,
                "text_type": code_to_label("text_type", text_type) if text_type else None,
                "content_audience_code": content_audience_code,
                "content_audience": code_to_label("content_audience", content_audience_code) if content_audience_code else None,
                "text_value": raw_text,
                "textformat": fmt,
                "source_title": source_title,
            }
        )
        if text_type == "02":
            book.short_description = raw_text
        elif text_type == "03":
            book.description = raw_text

    for sr in _all_children(cd, "SupportingResource"):
        content_type = _child_text(sr, "ResourceContentType", "")
        for rv in _all_children(sr, "ResourceVersion"):
            link = _child_text(rv, "ResourceLink", "")
            if link:
                media.append(
                    {
                        "resource_type_code": content_type,
                        "resource_link": link,
                    }
                )
                # Front cover
                if content_type == "01" and not book.cover_url:
                    book.cover_url = link

    book.texts = texts
    book.media = media


def _parse_publishing_detail(pd: etree._Element, book: Book) -> None:
    book.blocks_present.append("PublishingDetail")

    for imprint in _all_children(pd, "Imprint"):
        book.imprint_name = _child_text(imprint, "ImprintName", "")
        break

    for pub in _all_children(pd, "Publisher"):
        role = _child_text(pub, "PublishingRole", "")
        if role == "01":
            book.publisher_name = _child_text(pub, "PublisherName", "")
            break

    book.city_of_publication = _child_text(pd, "CityOfPublication", "")
    book.country_of_publication = _child_text(pd, "CountryOfPublication", "")

    status_code = _child_text(pd, "PublishingStatus", "")
    book.publishing_status_code = status_code
    if status_code:
        book.publishing_status = code_to_label("publishing_status", status_code)

    # Publication date — role 01 = publication date
    for pub_date in _all_children(pd, "PublishingDate"):
        role = _child_text(pub_date, "PublishingDateRole", "")
        if role == "01":
            raw = _child_text(pub_date, "Date", "")
            book.publication_date = _parse_date(raw)
            break

    # Sales rights — take first SalesRightsType 01 territory as primary rights
    for sr in _all_children(pd, "SalesRights"):
        sr_type = _child_text(sr, "SalesRightsType", "")
        if sr_type == "01":
            for terr in _all_children(sr, "Territory"):
                book.rights_countries_included = _child_text(terr, "CountriesIncluded", "")
                book.rights_countries_excluded = _child_text(terr, "CountriesExcluded", "")
                book.rights_regions = _child_text(terr, "RegionsIncluded", "")
            break


def _parse_product_supply(ps: etree._Element, book: Book) -> None:
    book.blocks_present.append("ProductSupply")

    market_ref = _child_text(ps, "MarketReference", "")
    market_status_code = None
    market_date_val = None

    mpd = None
    for child in ps:
        if _strip_ns(child.tag) == "MarketPublishingDetail":
            mpd = child
            break
    if mpd is not None:
        market_status_code = _child_text(mpd, "MarketPublishingStatus", "")
        for md in _all_children(mpd, "MarketDate"):
            role = _child_text(md, "MarketDateRole", "")
            if role == "01":
                market_date_val = _parse_date(_child_text(md, "Date", ""))
                break

    for sd in _all_children(ps, "SupplyDetail"):
        supplier_name = None
        supplier_role_code = None
        availability_code = None

        for supplier in _all_children(sd, "Supplier"):
            supplier_role_code = _child_text(supplier, "SupplierRole", "")
            supplier_name = _child_text(supplier, "SupplierName", "")
            break

        avail_code = _child_text(sd, "ProductAvailability", "")
        availability_code = avail_code
        availability = code_to_label("availability", avail_code) if avail_code else None

        # First price availability becomes book-level
        if not book.availability_code and availability_code:
            book.availability_code = availability_code
            book.availability = availability

        for price_elem in _all_children(sd, "Price"):
            price_type_code = _child_text(price_elem, "PriceType", "")
            price_status_code = _child_text(price_elem, "PriceStatus", "")
            amount_str = _child_text(price_elem, "PriceAmount", "")
            price_amount = float(amount_str) if amount_str else None
            currency_code = _child_text(price_elem, "CurrencyCode", "")

            countries_included = None
            countries_excluded = None
            regions_included = None
            for terr in _all_children(price_elem, "Territory"):
                countries_included = _child_text(terr, "CountriesIncluded", "")
                countries_excluded = _child_text(terr, "CountriesExcluded", "")
                regions_included = _child_text(terr, "RegionsIncluded", "")
                break

            discount_type = None
            discount_code_val = None
            discount_percent = None
            for dc in _all_children(price_elem, "DiscountCoded"):
                discount_type = _child_text(dc, "DiscountCodeType", "")
                discount_code_val = _child_text(dc, "DiscountCode", "")
                break
            for disc in _all_children(price_elem, "Discount"):
                pct_str = _child_text(disc, "DiscountPercent", "")
                discount_percent = float(pct_str) if pct_str else None
                break

            tax_type = None
            tax_rate_code = None
            tax_rate_pct = None
            taxable_amt = None
            tax_amt = None
            for tax_elem in _all_children(price_elem, "Tax"):
                tax_type = _child_text(tax_elem, "TaxType", "")
                tax_rate_code = _child_text(tax_elem, "TaxRateCode", "")
                pct_str = _child_text(tax_elem, "TaxRatePercent", "")
                tax_rate_pct = float(pct_str) if pct_str else None
                ta_str = _child_text(tax_elem, "TaxableAmount", "")
                taxable_amt = float(ta_str) if ta_str else None
                t_str = _child_text(tax_elem, "TaxAmount", "")
                tax_amt = float(t_str) if t_str else None
                break

            book.prices.append(
                Price(
                    supplier_name=supplier_name,
                    supplier_role_code=supplier_role_code,
                    availability_code=availability_code,
                    availability=availability,
                    price_type_code=price_type_code,
                    price_status_code=price_status_code,
                    price_amount=price_amount,
                    currency_code=currency_code,
                    countries_included=countries_included,
                    countries_excluded=countries_excluded,
                    regions_included=regions_included,
                    discount_code_type_code=discount_type,
                    discount_code=discount_code_val,
                    discount_percent=discount_percent,
                    tax_type_code=tax_type,
                    tax_rate_code=tax_rate_code,
                    tax_rate_percent=tax_rate_pct,
                    taxable_amount=taxable_amt,
                    tax_amount=tax_amt,
                    market_reference=market_ref,
                    market_publishing_status_code=market_status_code,
                    market_date=market_date_val,
                )
            )


def _parse_product(product_elem: etree._Element) -> Book:
    record_ref = _child_text(product_elem, "RecordReference", "") or ""
    notif_code = _child_text(product_elem, "NotificationType", "")

    book = Book(
        record_reference=record_ref,
        notification_type_code=notif_code,
    )

    # Product identifiers
    identifiers = []
    for pi in _all_children(product_elem, "ProductIdentifier"):
        id_type = _child_text(pi, "ProductIDType", "")
        id_value = _child_text(pi, "IDValue", "")
        if id_type == "03":
            # EAN-13 / GTIN-13
            book.gtin13 = id_value
        elif id_type == "15":
            # ISBN-13
            book.isbn13 = id_value
        elif id_type == "02":
            # ISBN-10
            book.isbn10 = id_value
        else:
            identifiers.append({"id_type_code": id_type, "id_value": id_value})
    book.identifiers = identifiers

    # Parse each block
    for child in product_elem:
        local = _strip_ns(child.tag)
        if local == "DescriptiveDetail":
            _parse_descriptive_detail(child, book)
        elif local == "CollateralDetail":
            _parse_collateral_detail(child, book)
        elif local == "PublishingDetail":
            _parse_publishing_detail(child, book)
        elif local == "ProductSupply":
            _parse_product_supply(child, book)

    return book


def parse_onix3(file_path: str) -> tuple[Feed, list[Book]]:
    """Parses ONIX 3.x file using iterparse for memory efficiency."""
    books: list[Book] = []
    feed_meta: dict = {}
    header_parsed = False

    context = etree.iterparse(file_path, events=("end",), recover=True)

    for event, elem in context:
        local = _strip_ns(elem.tag)

        if not header_parsed and local == "Header":
            feed_meta = _parse_header(elem)
            header_parsed = True
            elem.clear()
            continue

        if local == "Product":
            book = _parse_product(elem)
            books.append(book)
            elem.clear()
            continue

        # Release the root children once processed
        parent = elem.getparent()
        if parent is not None and _strip_ns(parent.tag) in ("ONIXMessage", "ONIXmessage"):
            elem.clear()

    # Build Feed — detect version from file (first 512 bytes)
    from parser.detect import detect_onix_version

    version = detect_onix_version(file_path)
    import os

    feed = Feed(
        source_file=os.path.basename(file_path),
        onix_version=version,
        sender_name=feed_meta.get("sender_name"),
        sender_email=feed_meta.get("sender_email"),
        sent_at=feed_meta.get("sent_at"),
        source_type="file",
    )

    return feed, books
