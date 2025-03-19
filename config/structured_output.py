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

"""Structured output types for image labeling."""

import enum
from typing_extensions import TypedDict


class ImageType(str, enum.Enum):
  """Image type classification enum."""

  SILO = 'silo'
  STYLIZED_SILO = 'stylized_silo'
  LIFESTYLE = 'lifestyle'
  GROUP = 'group'
  CLOSEUP = 'closeup'
  SWATCH = 'swatch'
  UNKNOWN = 'unknown'


class LabeledImage(TypedDict):
  """Structured Output for image labeling prompt.

  Your prompt should be structured to return an instance of this class for each
  image analyzed.

  Allowed types: str, enum.Enum, int, float, bool, list[AllowedType]
  """

  type: ImageType
