"""Curated catalog of common bikes: the only way to name a bike (specs/004-bike-builder).

Reference data, not a table: it ships with the app. A bike's display name is "Make Model" and
its type is the catalog category. Importable without FastAPI (constitution Principle II).
"""

from __future__ import annotations

from dataclasses import dataclass

CATEGORY_LABELS = {
    "road": "Road",
    "gravel": "Gravel",
    "mountain": "Mountain",
    "hybrid": "Hybrid",
    "e-bike": "E-bike",
}


@dataclass(frozen=True)
class BikeCatalogEntry:
    id: str
    make: str
    model: str
    category: str


_ENTRIES: tuple[BikeCatalogEntry, ...] = (
    BikeCatalogEntry("trek-domane", "Trek", "Domane", "road"),
    BikeCatalogEntry("trek-emonda", "Trek", "Emonda", "road"),
    BikeCatalogEntry("trek-madone", "Trek", "Madone", "road"),
    BikeCatalogEntry("specialized-tarmac", "Specialized", "Tarmac", "road"),
    BikeCatalogEntry("specialized-roubaix", "Specialized", "Roubaix", "road"),
    BikeCatalogEntry("specialized-aethos", "Specialized", "Aethos", "road"),
    BikeCatalogEntry("giant-tcr", "Giant", "TCR", "road"),
    BikeCatalogEntry("giant-defy", "Giant", "Defy", "road"),
    BikeCatalogEntry("giant-propel", "Giant", "Propel", "road"),
    BikeCatalogEntry("cannondale-supersix-evo", "Cannondale", "SuperSix EVO", "road"),
    BikeCatalogEntry("cannondale-synapse", "Cannondale", "Synapse", "road"),
    BikeCatalogEntry("canyon-ultimate", "Canyon", "Ultimate", "road"),
    BikeCatalogEntry("canyon-endurace", "Canyon", "Endurace", "road"),
    BikeCatalogEntry("canyon-aeroad", "Canyon", "Aeroad", "road"),
    BikeCatalogEntry("cervelo-s5", "Cervelo", "S5", "road"),
    BikeCatalogEntry("cervelo-r5", "Cervelo", "R5", "road"),
    BikeCatalogEntry("pinarello-dogma-f", "Pinarello", "Dogma F", "road"),
    BikeCatalogEntry("bmc-teammachine", "BMC", "Teammachine", "road"),
    BikeCatalogEntry("scott-addict", "Scott", "Addict", "road"),
    BikeCatalogEntry("bianchi-oltre", "Bianchi", "Oltre", "road"),
    BikeCatalogEntry("orbea-orca", "Orbea", "Orca", "road"),
    BikeCatalogEntry("specialized-diverge", "Specialized", "Diverge", "gravel"),
    BikeCatalogEntry("trek-checkpoint", "Trek", "Checkpoint", "gravel"),
    BikeCatalogEntry("canyon-grizl", "Canyon", "Grizl", "gravel"),
    BikeCatalogEntry("giant-revolt", "Giant", "Revolt", "gravel"),
    BikeCatalogEntry("cannondale-topstone", "Cannondale", "Topstone", "gravel"),
    BikeCatalogEntry("salsa-warbird", "Salsa", "Warbird", "gravel"),
    BikeCatalogEntry("salsa-journeyman", "Salsa", "Journeyman", "gravel"),
    BikeCatalogEntry("surly-midnight-special", "Surly", "Midnight Special", "gravel"),
    BikeCatalogEntry("surly-cross-check", "Surly", "Cross-Check", "gravel"),
    BikeCatalogEntry("niner-rlt", "Niner", "RLT", "gravel"),
    BikeCatalogEntry("cervelo-aspero", "Cervelo", "Aspero", "gravel"),
    BikeCatalogEntry("orbea-terra", "Orbea", "Terra", "gravel"),
    BikeCatalogEntry("santa-cruz-stigmata", "Santa Cruz", "Stigmata", "gravel"),
    BikeCatalogEntry("trek-fuel-ex", "Trek", "Fuel EX", "mountain"),
    BikeCatalogEntry("trek-marlin", "Trek", "Marlin", "mountain"),
    BikeCatalogEntry("trek-top-fuel", "Trek", "Top Fuel", "mountain"),
    BikeCatalogEntry("specialized-stumpjumper", "Specialized", "Stumpjumper", "mountain"),
    BikeCatalogEntry("specialized-rockhopper", "Specialized", "Rockhopper", "mountain"),
    BikeCatalogEntry("specialized-epic", "Specialized", "Epic", "mountain"),
    BikeCatalogEntry("giant-talon", "Giant", "Talon", "mountain"),
    BikeCatalogEntry("giant-trance", "Giant", "Trance", "mountain"),
    BikeCatalogEntry("santa-cruz-hightower", "Santa Cruz", "Hightower", "mountain"),
    BikeCatalogEntry("santa-cruz-bronson", "Santa Cruz", "Bronson", "mountain"),
    BikeCatalogEntry("yeti-sb130", "Yeti", "SB130", "mountain"),
    BikeCatalogEntry("canyon-spectral", "Canyon", "Spectral", "mountain"),
    BikeCatalogEntry("rocky-mountain-instinct", "Rocky Mountain", "Instinct", "mountain"),
    BikeCatalogEntry("cannondale-scalpel", "Cannondale", "Scalpel", "mountain"),
    BikeCatalogEntry("trek-fx", "Trek", "FX", "hybrid"),
    BikeCatalogEntry("trek-dual-sport", "Trek", "Dual Sport", "hybrid"),
    BikeCatalogEntry("specialized-sirrus", "Specialized", "Sirrus", "hybrid"),
    BikeCatalogEntry("giant-escape", "Giant", "Escape", "hybrid"),
    BikeCatalogEntry("cannondale-quick", "Cannondale", "Quick", "hybrid"),
    BikeCatalogEntry("raleigh-cadent", "Raleigh", "Cadent", "hybrid"),
    BikeCatalogEntry("marin-larkspur", "Marin", "Larkspur", "hybrid"),
    BikeCatalogEntry("specialized-turbo-vado", "Specialized", "Turbo Vado", "e-bike"),
    BikeCatalogEntry("specialized-turbo-levo", "Specialized", "Turbo Levo", "e-bike"),
    BikeCatalogEntry("trek-domane-plus", "Trek", "Domane+", "e-bike"),
    BikeCatalogEntry("trek-powerfly", "Trek", "Powerfly", "e-bike"),
    BikeCatalogEntry("giant-explore-e-plus", "Giant", "Explore E+", "e-bike"),
    BikeCatalogEntry("cannondale-tesoro-neo", "Cannondale", "Tesoro Neo", "e-bike"),
    BikeCatalogEntry("canyon-pathlite-on", "Canyon", "Pathlite:ON", "e-bike"),
    BikeCatalogEntry("rad-power-radrunner", "Rad Power", "RadRunner", "e-bike"),
    BikeCatalogEntry("aventon-level", "Aventon", "Level", "e-bike"),
    BikeCatalogEntry("brompton-electric", "Brompton", "Electric", "e-bike"),
)

_BY_ID = {entry.id: entry for entry in _ENTRIES}


def all_entries() -> list[BikeCatalogEntry]:
    return list(_ENTRIES)


def get(entry_id: object) -> BikeCatalogEntry | None:
    """The entry for a catalog id, or None for anything unknown or malformed."""
    return _BY_ID.get(entry_id) if isinstance(entry_id, str) else None


def display_name(entry: BikeCatalogEntry) -> str:
    return f"{entry.make} {entry.model}"


def grouped() -> list[tuple[str, list[BikeCatalogEntry]]]:
    """Entries grouped by category label (in catalog order), each sorted by make then model."""
    groups = []
    for category, label in CATEGORY_LABELS.items():
        entries = sorted(
            (e for e in _ENTRIES if e.category == category), key=lambda e: (e.make, e.model)
        )
        groups.append((label, entries))
    return groups
