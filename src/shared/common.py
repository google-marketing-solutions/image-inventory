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
