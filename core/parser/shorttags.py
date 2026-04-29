"""ONIX short tag → reference name mapping.

Derived by comparing the official ONIX 3.1 sample files and XSD (reference vs short).
ONIX 2.1 shares most element codes with ONIX 3.x; compound elements use lowercase names.
"""

from lxml import etree

# Short tag code → reference element name.
# Compound (composite) elements use lowercase reference names (no codes).
_SHORT_TO_REF: dict[str, str] = {
    # Root
    "onixmessage": "ONIXMessage",
    # Header
    "header": "Header",
    "sender": "Sender",
    "x298": "SenderName",
    "x299": "ContactName",
    "j270": "TelephoneNumber",
    "j272": "EmailAddress",
    "addressee": "Addressee",
    "x300": "AddresseeName",
    "m180": "MessageNumber",
    "x307": "SentDateTime",
    "m183": "MessageNote",
    # Product top-level
    "product": "Product",
    "a001": "RecordReference",
    "a002": "NotificationType",
    "a194": "RecordSourceType",
    "recordsourceidentifier": "RecordSourceIdentifier",
    "x311": "RecordSourceIDType",
    "a197": "RecordSourceName",
    # ProductIdentifier
    "productidentifier": "ProductIdentifier",
    "b221": "ProductIDType",
    "b244": "IDValue",
    "b233": "IDTypeName",
    # Block 1: Descriptive Detail
    "descriptivedetail": "DescriptiveDetail",
    "x314": "ProductComposition",
    "b012": "ProductForm",
    "b333": "ProductFormDetail",
    # ProductFormFeature
    "productformfeature": "ProductFormFeature",
    "b334": "ProductFormFeatureType",
    "b335": "ProductFormFeatureValue",
    # Measure
    "measure": "Measure",
    "x315": "MeasureType",
    "c094": "Measurement",
    "c095": "MeasureUnitCode",
    "x316": "CountryOfManufacture",
    # ProductClassification
    "productclassification": "ProductClassification",
    "b274": "ProductClassificationType",
    "b275": "ProductClassificationCode",
    # Collection / Series
    "collection": "Collection",
    "x329": "CollectionType",
    "series": "Series",
    # Title
    "titledetail": "TitleDetail",
    "b202": "TitleType",
    "titleelement": "TitleElement",
    "b034": "SequenceNumber",
    "x409": "TitleElementLevel",
    "b030": "TitlePrefix",
    "b031": "TitleWithoutPrefix",
    "b029": "Subtitle",
    "b032": "TitleWithPrefix",
    "b203": "TitleText",
    "x501": "NoPrefix",
    "x410": "PartNumber",
    # ONIX 2.1 title composite
    "title": "Title",
    # Contributor
    "contributor": "Contributor",
    "b035": "ContributorRole",
    "x412": "FromLanguage",
    "nameidentifier": "NameIdentifier",
    "x415": "NameIDType",
    "b036": "PersonName",
    "b037": "PersonNameInverted",
    "b038": "TitlesBeforeNames",
    "b039": "NamesBeforeKey",
    "b040": "KeyNames",
    "b044": "BiographicalNote",
    "b049": "ContributorStatement",
    # ONIX 2.1 contributor identifier
    "personnameidentifier": "PersonNameIdentifier",
    "b250": "PersonNameIDType",
    # Edition
    "n386": "NoEdition",
    "b057": "EditionNumber",
    "b058": "EditionStatement",
    # Language
    "language": "Language",
    "b253": "LanguageRole",
    "b252": "LanguageCode",
    # Extent
    "extent": "Extent",
    "b218": "ExtentType",
    "b219": "ExtentValue",
    "b220": "ExtentUnit",
    # Subject
    "subject": "Subject",
    "x425": "MainSubject",
    "b067": "SubjectSchemeIdentifier",
    "b068": "SubjectSchemeVersion",
    "b069": "SubjectCode",
    "b070": "SubjectHeadingText",
    # Audience
    "audience": "Audience",
    "b204": "AudienceCodeType",
    "b206": "AudienceCodeValue",
    # Block 2: Collateral Detail
    "collateraldetail": "CollateralDetail",
    "textcontent": "TextContent",
    "x426": "TextType",
    "x427": "ContentAudience",
    "d104": "Text",
    "x428": "SourceTitle",
    # CitedContent
    "citedcontent": "CitedContent",
    "x430": "CitedContentType",
    "x431": "SourceType",
    "x434": "CitationNote",
    # ContentDate
    "contentdate": "ContentDate",
    "x429": "ContentDateRole",
    "b306": "Date",
    # SupportingResource
    "supportingresource": "SupportingResource",
    "x436": "ResourceContentType",
    "x437": "ResourceMode",
    "resourceversion": "ResourceVersion",
    "x441": "ResourceForm",
    "resourceversionfeature": "ResourceVersionFeature",
    "x442": "ResourceVersionFeatureType",
    "x439": "FeatureValue",
    "x435": "ResourceLink",
    # Block 4: Publishing Detail
    "publishingdetail": "PublishingDetail",
    "imprint": "Imprint",
    "b079": "ImprintName",
    "publisher": "Publisher",
    "b291": "PublishingRole",
    "publisheridentifier": "PublisherIdentifier",
    "x447": "PublisherIDType",
    "b081": "PublisherName",
    "website": "Website",
    "b367": "WebsiteRole",
    "b295": "WebsiteLink",
    "b209": "CityOfPublication",
    "b083": "CountryOfPublication",
    "b394": "PublishingStatus",
    "publishingdate": "PublishingDate",
    "x448": "PublishingDateRole",
    # Copyright
    "copyrightstatement": "CopyrightStatement",
    "copyrightowner": "CopyrightOwner",
    "b087": "CopyrightYear",
    # Sales Rights
    "salesrights": "SalesRights",
    "b089": "SalesRightsType",
    "territory": "Territory",
    "x449": "CountriesIncluded",
    "x450": "RegionsIncluded",
    "x451": "CountriesExcluded",
    # Related Material
    "relatedmaterial": "RelatedMaterial",
    "relatedwork": "RelatedWork",
    "x454": "WorkRelationCode",
    "workidentifier": "WorkIdentifier",
    "b201": "WorkIDType",
    "relatedproduct": "RelatedProduct",
    "x455": "ProductRelationCode",
    # Block 9: Product Supply
    "productsupply": "ProductSupply",
    "x587": "MarketReference",
    "market": "Market",
    "marketpublishingdetail": "MarketPublishingDetail",
    "j407": "MarketPublishingStatus",
    "marketdate": "MarketDate",
    "j408": "MarketDateRole",
    "supplydetail": "SupplyDetail",
    "supplier": "Supplier",
    "j292": "SupplierRole",
    "supplieridentifier": "SupplierIdentifier",
    "j345": "SupplierIDType",
    "j137": "SupplierName",
    "returnsconditions": "ReturnsConditions",
    "j268": "ReturnsCodeType",
    "j269": "ReturnsCode",
    "j396": "ProductAvailability",
    "j145": "PackQuantity",
    # Price
    "price": "Price",
    "x462": "PriceType",
    "discountcoded": "DiscountCoded",
    "j363": "DiscountCodeType",
    "j364": "DiscountCode",
    "j266": "PriceStatus",
    "j151": "PriceAmount",
    "j152": "CurrencyCode",
    "tax": "Tax",
    "x470": "TaxType",
    "x471": "TaxRateCode",
    "x472": "TaxRatePercent",
    "x473": "TaxableAmount",
    "x474": "TaxAmount",
    "x301": "PrintedOnProduct",
    "x313": "PositionOnProduct",
    "discount": "Discount",
    "j267": "DiscountPercent",
    # ONIX 2.1 price uses PriceTypeCode not PriceType
    "j148": "PriceTypeCode",
    # ONIX 2.1 supply / media
    "mediafile": "MediaFile",
    "f114": "MediaFileTypeCode",
    "f116": "MediaFileLink",
}


def normalize_tag(local_name: str) -> str:
    """Converts an ONIX short tag local name to its reference name.
    Unknown tags are returned as-is (already reference names or unrecognised)."""
    return _SHORT_TO_REF.get(local_name, local_name)


def normalize_elem_tree(elem: etree._Element) -> None:
    """Renames all short tag element names in an lxml element tree to reference names.
    Operates in-place; safe to call on both short tag and reference tag files."""
    for e in elem.iter():
        if not isinstance(e.tag, str):
            continue
        if e.tag and e.tag[0] == "{":
            ns, local = e.tag[1:].split("}", 1)
            normalized = normalize_tag(local)
            if normalized != local:
                e.tag = f"{{{ns}}}{normalized}"
        else:
            normalized = normalize_tag(e.tag)
            if normalized != e.tag:
                e.tag = normalized
