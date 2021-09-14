from django.core.management.base import BaseCommand
from django.db import transaction

from countries.models import Country
from report.models import OverheardAtChoice, ReportedViaChoice, Domain, StatusChoice, SourceChoice, PriorityChoice


class Command(BaseCommand):
    help = "load master tables"

    def handle(self, *args, **kwargs):
        import_master_tables()


def import_master_tables():
    import_countries()
    import_priority_values()
    import_status_values()
    import_source_values()
    import_reported_via_values()
    import_overheard_at_values()
    import_domains()


def import_countries():
    with transaction.atomic():

        lines = [
            ("AF", "Afghanistan"),
            ("AL", "Albania"),
            ("DZ", "Algeria"),
            ("AS", "American Samoa"),
            ("AO", "Angola"),
            ("AG", "Antigua and Barbuda"),
            ("AR", "Argentina"),
            ("AM", "Armenia"),
            ("AU", "Australia"),
            ("AT", "Austria"),
            ("AZ", "Azerbaijan"),
            ("BS", "Bahamas, The"),
            ("BH", "Bahrain"),
            ("BD", "Bangladesh"),
            ("BB", "Barbados"),
            ("BY", "Belarus"),
            ("BE", "Belgium"),
            ("BZ", "Belize"),
            ("BJ", "Benin"),
            ("BT", "Bhutan"),
            ("BO", "Bolivia"),
            ("BA", "Bosnia and Herzegovina"),
            ("BW", "Botswana"),
            ("BR", "Brazil"),
            ("BN", "Brunei Darussalam"),
            ("BG", "Bulgaria"),
            ("BF", "Burkina Faso"),
            ("KH", "Cambodia"),
            ("CM", "Cameroon"),
            ("CA", "Canada"),
            ("CF", "Central African Republic"),
            ("TD", "Chad"),
            ("CL", "Chile"),
            ("CN", "China"),
            ("CO", "Colombia"),
            ("KM", "Comoros"),
            ("CD", "Congo, Dem. Rep."),
            ("CG", "Congo, Rep."),
            ("CR", "Costa Rica"),
            ("CI", "Côte d'Ivoire"),
            ("HR", "Croatia"),
            ("CU", "Cuba"),
            ("CY", "Cyprus"),
            ("CZ", "Czech Republic"),
            ("DK", "Denmark"),
            ("DJ", "Djibouti"),
            ("DM", "Dominica"),
            ("DO", "Dominican Republic"),
            ("EC", "Ecuador"),
            ("EG", "Egypt, Arab Rep."),
            ("SV", "El Salvador"),
            ("GQ", "Equatorial Guinea"),
            ("ER", "Eritrea"),
            ("EE", "Estonia"),
            ("ET", "Ethiopia"),
            ("FJ", "Fiji"),
            ("FI", "Finland"),
            ("FR", "France"),
            ("GA", "Gabon"),
            ("GM", "Gambia, The"),
            ("GE", "Georgia"),
            ("DE", "Germany"),
            ("GH", "Ghana"),
            ("GR", "Greece"),
            ("GD", "Grenada"),
            ("GT", "Guatemala"),
            ("GN", "Guinea"),
            ("GW", "Guinea-Bissau"),
            ("GY", "Guyana"),
            ("HT", "Haiti"),
            ("HN", "Honduras"),
            ("HU", "Hungary"),
            ("IS", "Iceland"),
            ("IN", "India"),
            ("ID", "Indonesia"),
            ("IR", "Iran, Islamic Rep."),
            ("IQ", "Iraq"),
            ("IE", "Ireland"),
            ("IL", "Israel"),
            ("IT", "Italy"),
            ("JM", "Jamaica"),
            ("JP", "Japan"),
            ("JO", "Jordan"),
            ("KZ", "Kazakhstan"),
            ("KE", "Kenya"),
            ("KI", "Kiribati"),
            ("KR", "Korea, Rep."),
            ("KW", "Kuwait"),
            ("KG", "Kyrgyz Republic"),
            ("LA", "Lao PDR"),
            ("LV", "Latvia"),
            ("LB", "Lebanon"),
            ("LS", "Lesotho"),
            ("LR", "Liberia"),
            ("LY", "Libya"),
            ("LT", "Lithuania"),
            ("LU", "Luxembourg"),
            ("MK", "Macedonia (North)"),
            ("MG", "Madagascar"),
            ("MW", "Malawi"),
            ("MY", "Malaysia"),
            ("MV", "Maldives"),
            ("ML", "Mali"),
            ("MT", "Malta"),
            ("MR", "Mauritania"),
            ("MU", "Mauritius"),
            ("MX", "Mexico"),
            ("FM", "Micronesia, Fed. Sts."),
            ("MD", "Moldova"),
            ("MN", "Mongolia"),
            ("ME", "Montenegro"),
            ("MA", "Morocco"),
            ("MZ", "Mozambique"),
            ("MM", "Myanmar"),
            ("NA", "Namibia"),
            ("NP", "Nepal"),
            ("NL", "Netherlands"),
            ("NZ", "New Zealand"),
            ("NI", "Nicaragua"),
            ("NE", "Niger"),
            ("NG", "Nigeria"),
            ("NO", "Norway"),
            ("OM", "Oman"),
            ("PK", "Pakistan"),
            ("PA", "Panama"),
            ("PG", "Papua New Guinea"),
            ("PY", "Paraguay"),
            ("PE", "Peru"),
            ("PH", "Philippines"),
            ("PL", "Poland"),
            ("PT", "Portugal"),
            ("QA", "Qatar"),
            ("RO", "Romania"),
            ("RU", "Russian Federation"),
            ("RW", "Rwanda"),
            ("WS", "Samoa"),
            ("ST", "São Tomé and Principe"),
            ("SA", "Saudi Arabia"),
            ("SN", "Senegal"),
            ("RS", "Serbia"),
            ("SC", "Seychelles"),
            ("SL", "Sierra Leone"),
            ("SG", "Singapore"),
            ("SK", "Slovak Republic"),
            ("SI", "Slovenia"),
            ("SB", "Solomon Islands"),
            ("ZA", "South Africa"),
            ("ES", "Spain"),
            ("LK", "Sri Lanka"),
            ("SO", "Somalia"),
            ("SD", "Sudan"),
            ("SS", "South Sudan"),
            ("SR", "Suriname"),
            ("SZ", "Eswatini (Swaziland)"),
            ("SE", "Sweden"),
            ("CH", "Switzerland"),
            ("TJ", "Tajikistan"),
            ("TZ", "Tanzania"),
            ("TH", "Thailand"),
            ("TL", "Timor-Leste"),
            ("TG", "Togo"),
            ("TO", "Tonga"),
            ("TT", "Trinidad and Tobago"),
            ("TN", "Tunisia"),
            ("TR", "Turkey"),
            ("TM", "Turkmenistan"),
            ("UG", "Uganda"),
            ("UA", "Ukraine"),
            ("AE", "United Arab Emirates"),
            ("GB", "United Kingdom"),
            ("US", "United States"),
            ("UY", "Uruguay"),
            ("VE", "Venezuela, RB"),
            ("VN", "Vietnam"),
            ("ZM", "Zambia"),
            ("ZW", "Zimbabwe"),
        ]
        for line in lines:

            country = Country.objects.filter(iso_code=line[0]).first()
            if not country:
                country = Country()
                country.iso_code = line[0]
            country.name = line[1]

            country.save()

        print("imported countries")


def import_priority_values():
    with transaction.atomic():
        priority_values = ['Low', 'Medium', "High"]
        for value in priority_values:
            PriorityChoice.objects.get_or_create(name=value)


def import_status_values():
    with transaction.atomic():
        # load values for status
        status_values = [
            "New / uninvestigated",
            "Under investigation",
            "Probably true",
            "Probably false",
            "Confirmed true",
            "Confirmed false",
            "Impossible to verify",
            "Impossible to verify but probably true",
            "Impossible to verify but probably false"]
        for value in status_values:
            StatusChoice.objects.get_or_create(name=value)


def import_source_values():
    with transaction.atomic():
        # load values for source
        source_values = ['Overheard', "Whatsapp", "Phone", "Social Media"]
        for value in source_values:
            SourceChoice.objects.get_or_create(name=value)


def import_reported_via_values():
    with transaction.atomic():
        # load values for reported via
        reported_via_values = ['Internet', "Email", "SMS", "Voice / telephone", "Walk-in / in person", "Other"]
        for value in reported_via_values:
            ReportedViaChoice.objects.get_or_create(name=value)


def import_overheard_at_values():
    with transaction.atomic():
        # load values for overheard at
        overheard_at_values = ['Workplace', "Neighbourhood", "Market", "Place of Worship", "Street"]
        for value in overheard_at_values:
            OverheardAtChoice.objects.get_or_create(name=value)


def import_domains():
    # load domains
    domains = [
        (112, "peacefultruth.org", "Peaceful Truth"),
        (113, "unahakika.org", "Una Hakika"),
        (115, "kijijichaamani.org", "Kijiji Cha Amaani"),
        (124, "hagigawahid.org", "Hagiga Wahid"),
        (133, "runtuwaanabad.org", "Runtu Waa Nabad"),
        (137, "lka.wikirumours.org", "WR - Sri Lanka"),
        (1, "wikirumours.org", "Wikirumours"),
    ]
    with transaction.atomic():
        for domain in domains:
            existing_domain = Domain.objects.filter(domain=domain[1]).first()
            if not existing_domain:
                domain_object = Domain()
                domain_object.id = domain[0]
                domain_object.domain = str(domain[1].strip())
                domain_object.name = str(domain[2].strip())
                domain_object.save()
