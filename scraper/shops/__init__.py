from .morimori import MorimoriScraper
from .homura import HomuraScraper
from .rudeya import RudeyaScraper
from .runto import RuntoScraper
from .icchome import IcchomeScraper
from .oku import OkuScraper
from .kaikyo import KaikyoScraper
from .sommelier import SommelierScraper
from .collect_tendo import CollectTendoScraper

ALL_SCRAPERS = [
    MorimoriScraper,
    HomuraScraper,
    RudeyaScraper,
    RuntoScraper,
    IcchomeScraper,
    OkuScraper,
    KaikyoScraper,
    SommelierScraper,
    CollectTendoScraper,
]
