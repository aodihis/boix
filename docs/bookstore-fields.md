# ONIX 3.x Field Mapping

Reference table mapping ONIX 3.x element paths to database columns.

| ONIX 3.x Element | DB Table | Column | Notes |
|---|---|---|---|
| RecordReference | books | record_reference | Unique key for upsert |
| NotificationType | books | notification_type_code | Drives push queue logic |
| ProductIdentifier[15]/IDValue | books | isbn13 | ProductIDType 15 = ISBN-13 |
| ProductIdentifier[02]/IDValue | books | isbn10 | ProductIDType 02 = ISBN-10 |
| ProductIdentifier[13]/IDValue | books | gtin13 | ProductIDType 13 = GTIN-13 |
| DescriptiveDetail/TitleDetail/TitleElement/TitleText | books | title | TitleType 01 |
| DescriptiveDetail/TitleDetail/TitleElement/Subtitle | books | subtitle | |
| DescriptiveDetail/TitleDetail/TitleElement/TitleWithoutKey | books | full_title | Combined title and subtitle |
| DescriptiveDetail/Series/SeriesIdentifier/IDValue | books | series_name | Series title |
| DescriptiveDetail/Series/SeriesIdentifier/SeriesNumber | books | series_number | Position within series |
| DescriptiveDetail/Contributor/NamesBeforeKey | book_contributors | names_before_key | |
| DescriptiveDetail/Contributor/KeyNames | book_contributors | key_names | |
| DescriptiveDetail/Contributor/ContributorRole | book_contributors | role_code | e.g. A01=Author, B01=Editor |
| DescriptiveDetail/Contributor/SequenceNumber | book_contributors | sequence_number | Display order |
| DescriptiveDetail/Contributor/BiographicalNote | book_contributors | biographical_note | Optional author bio |
| DescriptiveDetail/Subject/SubjectSchemeIdentifier | book_subjects | scheme_code | 10=BISAC, 93=Thema |
| DescriptiveDetail/Subject/SubjectCode | book_subjects | subject_code | E.g., FIC028000 for BISAC |
| DescriptiveDetail/Subject/SubjectHeadingText | book_subjects | subject_heading_text | Plain text heading |
| DescriptiveDetail/Subject/BASICMainSubject | book_subjects | is_main_subject | Boolean flag |
| DescriptiveDetail/ProductForm | books | product_form_code | BB=Hardback, BC=Paperback, etc. |
| DescriptiveDetail/ProductFormDetail | books | product_form | Human-readable label |
| DescriptiveDetail/EditionNumber | books | edition_number | E.g., "2" for second edition |
| DescriptiveDetail/EditionStatement | books | edition_statement | Full text, e.g., "2nd edition, revised" |
| DescriptiveDetail/Extent/ExtentValue | books | page_count | Number of pages |
| DescriptiveDetail/Measurement/MeasurementValue | books | height_mm, width_mm, thickness_mm | Dimensions in millimeters |
| DescriptiveDetail/Measurement/MeasurementValue (weight) | books | weight_g | Weight in grams |
| CollateralDetail/TextContent[03]/Text | books | description | TextType 03 = Long description |
| CollateralDetail/TextContent[02]/Text | books | short_description | TextType 02 = Short description |
| CollateralDetail/SupportingResource/ResourceVersion/ResourceLink | books | media (JSONB) | All media: cover images, video, audio |
| PublishingDetail/Publisher/PublisherName | books | publisher_name | PublishingRole 01 |
| PublishingDetail/PublisherPlace/CityName | books | city_of_publication | |
| PublishingDetail/PublisherPlace/CountryCode | books | country_of_publication | ISO 3166-1 two-letter code |
| PublishingDetail/Imprint/ImprintName | books | imprint_name | |
| PublishingDetail/PublishingDate[01]/Date | books | publication_date | DateRole 01, format YYYYMMDD |
| PublishingDetail/PublishingStatus | books | publishing_status_code | 04=Active, 00=Unspecified, etc. |
| PublishingDetail/PublishingStatus (label) | books | publishing_status | Human-readable status label |
| DescriptiveDetail/Language[01]/LanguageCode | books | language_code | 3-letter ISO 639-2 code |
| DescriptiveDetail/Language[02]/LanguageCode | books | original_language_code | Original work language |
| DescriptiveDetail/Language | books | languages (JSONB) | Array of all language codes with roles |
| ProductSupply/SupplyDetail/Price/PriceAmount | book_prices | price_amount | Decimal value |
| ProductSupply/SupplyDetail/Price/CurrencyCode | book_prices | currency_code | ISO 4217, e.g., USD, GBP, EUR |
| ProductSupply/SupplyDetail/Price/Territory/CountriesIncluded | book_prices | countries_included | ISO 3166-1 codes |
| ProductSupply/SupplyDetail/SupplierName | book_prices | supplier_name | Distributor/reseller name |
| ProductSupply/SupplyDetail/Availability/AvailabilityCode | books | availability_code | Supply status code |
| ProductSupply/SupplyDetail/Availability (label) | books | availability | Human-readable availability |
| Rights/RightsStatement/RightsTerritory/CountriesIncluded | books | rights_countries_included | JSONB array |
| Rights/RightsStatement/RightsTerritory/CountriesExcluded | books | rights_countries_excluded | JSONB array |
| Rights/RightsStatement/RightsTerritory/RightsRegion | books | rights_regions | JSONB array |
