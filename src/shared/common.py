# Copyright 2025 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Common dataclasses for Cloud Functions."""

import dataclasses
import json
from typing import Optional


class Error(Exception):
  """Generic Error class for module."""


class ProductFilterError(Error):
  """Error when product filter is invalid."""


@dataclasses.dataclass
class Product:
  """Product data class."""

  offer_id: str
  merchant_id: int
  aggregator_id: int
  title: str
  product_type: str
  brand: str
  image_link: Optional[str]
  additional_image_links: list[str]

  def to_json(self) -> str:
    """Returns a JSON string representation of the Product."""
    return json.dumps(dataclasses.asdict(self))


@dataclasses.dataclass
class ProductFilter:
  """Product filter dataclass."""

  product_type: Optional[str] = None
  brands: Optional[list[str]] = None
  offer_ids: Optional[list[str]] = None

  def __post_init__(self) -> None:
    if not self.product_type and not self.brands and not self.offer_ids:
      raise ProductFilterError(
          'At least one of product_type, brands, or offer_ids must be set.'
      )

  def get_sql_filter(self) -> str:
    """Generates GoogleSQL WHERE clause based on filter settings."""
    product_filters = []
    if self.product_type:
      product_filters.append(
          f'product_type LIKE "{self.product_type}%"'
      )
    if self.brands:
      brand_list = ','.join(
          [f'"{b.strip().lower() }"' for b in self.brands]
      )
      product_filters.append(f'brand IN ({brand_list})')
    if self.offer_ids:
      offer_list = ','.join(
          [f'"{s.strip().lower()}"' for s in self.offer_ids]
      )
      product_filters.append(f'offer_id IN ({offer_list})')
    return '\n AND '.join(product_filters)
