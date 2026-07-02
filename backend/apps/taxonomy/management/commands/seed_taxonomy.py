import re

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.taxonomy.models import TaxonomyFacet, TaxonomyValue
from apps.videos.constants import (
    ALL_TAXONOMY_FACETS,
    FACET_VALUE_SOURCE_OVERRIDES,
    MULTI_SELECT_FACETS,
)

FACET_HEADER_RE = re.compile(r"^([a-z][a-z0-9_]*):$")
SLUG_RE = re.compile(r"^[a-z0-9_]+$")


def humanize(slug: str) -> str:
    return slug.replace("_", " ").title()


def parse_taxonomy_txt(text: str) -> dict:
    """taxonomy.txt is free-form: "<facet>:" header lines followed by one or
    more lines of comma-separated slug values, blocks separated loosely by
    blank lines. Any token that isn't a plain slug (stray prose, trailing
    notes) is silently dropped rather than raising, since the file is a
    human-maintained note, not a strict format.
    """
    facets: dict[str, list[str]] = {}
    current = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        header = FACET_HEADER_RE.match(line)
        if header:
            current = header.group(1)
            facets.setdefault(current, [])
            continue
        if current is None:
            continue
        for token in line.split(","):
            token = token.strip()
            if SLUG_RE.match(token) and token not in facets[current]:
                facets[current].append(token)
    return facets


class Command(BaseCommand):
    help = "Seed TaxonomyFacet/TaxonomyValue rows from taxonomy.txt (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default=str(settings.TAXONOMY_TXT_PATH),
            help="Path to taxonomy.txt (defaults to settings.TAXONOMY_TXT_PATH)",
        )

    def handle(self, *args, **options):
        path = options["path"]
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as exc:
            raise CommandError(f"Could not read taxonomy file at {path}: {exc}")

        parsed = parse_taxonomy_txt(text)

        # secondary_requests has no dedicated section in taxonomy.txt -- it
        # reuses "request"'s values (see apps.videos.constants).
        for facet_key, source_key in FACET_VALUE_SOURCE_OVERRIDES.items():
            if source_key in parsed:
                parsed[facet_key] = list(parsed[source_key])

        missing = [f for f in ALL_TAXONOMY_FACETS if f not in parsed]
        if missing:
            self.stderr.write(
                self.style.WARNING(f"No values found in {path} for facets: {missing}")
            )

        created_facets = updated_facets = created_values = updated_values = 0

        with transaction.atomic():
            for order, facet_key in enumerate(ALL_TAXONOMY_FACETS):
                values = parsed.get(facet_key, [])
                facet, created = TaxonomyFacet.objects.update_or_create(
                    key=facet_key,
                    defaults={
                        "label": humanize(facet_key),
                        "multi_select": facet_key in MULTI_SELECT_FACETS,
                        "order": order,
                    },
                )
                created_facets += int(created)
                updated_facets += int(not created)

                for v_order, value in enumerate(values):
                    _, v_created = TaxonomyValue.objects.update_or_create(
                        facet=facet,
                        value=value,
                        defaults={"label": humanize(value), "order": v_order},
                    )
                    created_values += int(v_created)
                    updated_values += int(not v_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Facets: {created_facets} created, {updated_facets} updated. "
                f"Values: {created_values} created, {updated_values} updated."
            )
        )
