from aura_generator.blueprint import Blueprint, Entity, EntityField, Page, Relation


def test_blueprint_normalizes_names_and_slug():
    bp = Blueprint(
        name="Warehouse Management System",
        entities=[
            Entity(
                name="warehouse item",
                fields=[EntityField(name="Name")],
                relations=[Relation(name="Warehouse", target="warehouse")],
            )
        ],
    )
    assert bp.slug == "warehouse-management-system"
    e = bp.entities[0]
    assert e.name == "WarehouseItem"
    assert e.fields[0].name == "name"
    assert e.relations[0].name == "warehouse"
    assert e.relations[0].target == "Warehouse"


def test_ensure_default_pages_synthesizes_pages():
    bp = Blueprint(
        name="App",
        entities=[Entity(name="Product", fields=[EntityField(name="name")])],
    )
    assert bp.pages == []
    bp.ensure_default_pages()
    types = {p.type for p in bp.pages}
    assert {"dashboard", "list", "form", "detail"} <= types


def test_table_name_is_snake_plural():
    e = Entity(name="InventoryLevel", fields=[EntityField(name="quantity", type="integer")])
    assert e.table_name == "inventory_levels"


def test_ensure_default_pages_is_idempotent():
    bp = Blueprint(name="App", entities=[Entity(name="P", fields=[EntityField(name="n")])])
    bp.pages = [Page(type="dashboard", title="x")]
    bp.ensure_default_pages()
    assert len(bp.pages) == 1
