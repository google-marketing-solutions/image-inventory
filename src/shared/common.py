import dataclasses
import json
from typing import Optional


@dataclasses.dataclass
class Product:
  """Product data class."""

  offer_id: str
  merchant_id: int
  aggregator_id: int
  title: str
  product_type: str
  image_link: Optional[str]
  additional_image_links: list[str]

  def to_json(self) -> str:
    """Returns a JSON string representation of the Product."""
    return json.dumps(dataclasses.asdict(self))
