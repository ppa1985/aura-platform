"""Blueprint domain model.

An App Blueprint is a declarative, validated description of an application.
The Blueprint Engine produces one; every downstream component (schema generator,
component assembler, auto-coder, self-healer) consumes it.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from slugify import slugify

FieldType = Literal[
    "string",
    "text",
    "integer",
    "float",
    "decimal",
    "boolean",
    "date",
    "datetime",
    "uuid",
    "json",
]

PageType = Literal["dashboard", "list", "form", "detail"]


class EntityField(BaseModel):
    name: str
    type: FieldType = "string"
    required: bool = False
    unique: bool = False
    default: str | int | float | bool | None = None
    description: str | None = None

    @field_validator("name")
    @classmethod
    def _snake(cls, v: str) -> str:
        v = re.sub(r"[^a-zA-Z0-9_]", "_", v).strip("_").lower()
        if not v:
            raise ValueError("field name cannot be empty")
        return v


class Relation(BaseModel):
    """A foreign-key relation from this entity to another."""

    name: str  # field name on this entity (e.g. "warehouse")
    target: str  # target entity name (PascalCase)
    kind: Literal["many_to_one", "one_to_many"] = "many_to_one"
    required: bool = False

    @field_validator("name")
    @classmethod
    def _snake(cls, v: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_]", "_", v).strip("_").lower()

    @field_validator("target")
    @classmethod
    def _pascal_target(cls, v: str) -> str:
        parts = re.split(r"[^a-zA-Z0-9]+", v)
        return "".join(p[:1].upper() + p[1:] for p in parts if p) or v


class Entity(BaseModel):
    name: str  # PascalCase, e.g. "Product"
    description: str | None = None
    fields: list[EntityField] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _pascal(cls, v: str) -> str:
        parts = re.split(r"[^a-zA-Z0-9]+", v)
        v2 = "".join(p[:1].upper() + p[1:] for p in parts if p)
        if not v2:
            raise ValueError("entity name cannot be empty")
        return v2

    @property
    def table_name(self) -> str:
        # snake_case plural-ish; keep deterministic and simple
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", self.name).lower()
        return snake + "s"


class Page(BaseModel):
    type: PageType
    title: str
    entity: str | None = None  # PascalCase entity name (None for dashboard)
    description: str | None = None


class AIConfig(BaseModel):
    provider: Literal["ollama", "openai", "anthropic"] = "ollama"
    model: str = "llama3.2:3b"
    system_prompt: str | None = None


class Blueprint(BaseModel):
    name: str
    slug: str = ""
    description: str = ""
    entities: list[Entity] = Field(default_factory=list)
    pages: list[Page] = Field(default_factory=list)
    ai_enabled: bool = False
    ai_config: AIConfig | None = None

    @model_validator(mode="after")
    def _ensure_slug(self) -> "Blueprint":
        if not self.slug:
            self.slug = slugify(self.name) if self.name else ""
        else:
            self.slug = slugify(self.slug)
        return self

    def ensure_default_pages(self) -> None:
        """If the LLM produced no pages, synthesize sensible defaults."""
        if self.pages:
            return
        self.pages.append(Page(type="dashboard", title="Overview"))
        for e in self.entities:
            self.pages.append(Page(type="list", title=f"{e.name}s", entity=e.name))
            self.pages.append(Page(type="form", title=f"New {e.name}", entity=e.name))
            self.pages.append(Page(type="detail", title=f"{e.name} Detail", entity=e.name))
