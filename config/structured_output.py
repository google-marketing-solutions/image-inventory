"""Structured output types for image labeling."""

import enum
from typing import TypedDict


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
