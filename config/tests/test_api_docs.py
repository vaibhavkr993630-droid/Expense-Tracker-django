import pytest
import yaml
from django.core.management import call_command

pytestmark = pytest.mark.django_db

# Every endpoint of the API contract (docs/api-contract.md) as (METHOD, path-in-the-docs).
# /user (the legacy URL) is deliberately hidden from the docs: it duplicates /users/me.
DOCUMENTED_ENDPOINTS = {
    ("POST", "/signup"),
    ("POST", "/login"),
    ("GET", "/users/me"),
    ("PUT", "/users/me"),
    ("DELETE", "/users/me"),
    ("PATCH", "/users/change-password"),
    ("GET", "/expenses"),
    ("POST", "/expenses"),
    ("GET", "/expenses/{id}"),
    ("PUT", "/expenses/{id}"),
    ("DELETE", "/expenses/{id}"),
    ("GET", "/expenses/export/csv"),
    ("GET", "/expenses/export/pdf"),
    ("GET", "/expenses/summary/monthly"),
    ("GET", "/expenses/summary/category"),
    ("GET", "/expenses/summary/trend"),
    ("GET", "/budgets"),
    ("POST", "/budgets"),
    ("DELETE", "/budgets/{id}"),
    ("GET", "/budgets/alerts"),
    ("GET", "/healthy"),
}


@pytest.fixture(scope="module")
def generated_schema(tmp_path_factory, django_db_blocker):
    path = tmp_path_factory.mktemp("schema") / "schema.yml"
    # --validate checks the document against the OpenAPI spec; --fail-on-warn turns any
    # "could not guess serializer" style warning into a failure, so the docs cannot silently rot.
    with django_db_blocker.unblock():
        call_command("spectacular", "--validate", "--fail-on-warn", "--file", str(path))
    return yaml.safe_load(path.read_text())


def test_schema_generates_without_warnings_or_errors(generated_schema):
    assert generated_schema["openapi"].startswith("3.")
    assert generated_schema["info"]["title"] == "Expense Tracker API"


def test_every_contract_endpoint_is_documented_and_nothing_extra(generated_schema):
    documented = {
        (method.upper(), path)
        for path, operations in generated_schema["paths"].items()
        for method in operations
        if method in {"get", "post", "put", "patch", "delete"}
    }
    # PATCH /expenses/{id} is real (a ModelViewSet gives it for free) but is not in the old contract.
    assert documented - {("PATCH", "/expenses/{id}")} == DOCUMENTED_ENDPOINTS


def test_protected_endpoints_require_a_bearer_token_and_public_ones_do_not(generated_schema):
    paths = generated_schema["paths"]
    assert generated_schema["components"]["securitySchemes"]["jwtAuth"]["scheme"] == "bearer"
    assert paths["/expenses"]["get"]["security"] == [{"jwtAuth": []}]
    assert paths["/users/me"]["get"]["security"] == [{"jwtAuth": []}]
    for public in (paths["/login"]["post"], paths["/signup"]["post"], paths["/healthy"]["get"]):
        assert "security" not in public  # no token needed


def test_every_operation_has_a_tag_and_summary(generated_schema):
    for path, operations in generated_schema["paths"].items():
        for method, operation in operations.items():
            assert operation.get("tags"), f"{method} {path} has no tag"
            assert operation.get("summary"), f"{method} {path} has no summary"


def test_login_documents_form_and_json_bodies(generated_schema):
    content = generated_schema["paths"]["/login"]["post"]["requestBody"]["content"]
    assert set(content) == {"application/x-www-form-urlencoded", "application/json"}


def test_list_response_documents_the_expenses_envelope(generated_schema):
    response = generated_schema["paths"]["/expenses"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]
    component = response["schema"]["$ref"].split("/")[-1]  # the response points at a shared component
    properties = generated_schema["components"]["schemas"][component]["properties"]
    assert set(properties) == {"expenses", "page", "limit", "total"}


def test_export_endpoints_document_their_content_types(generated_schema):
    paths = generated_schema["paths"]
    assert "text/csv" in paths["/expenses/export/csv"]["get"]["responses"]["200"]["content"]
    assert "application/pdf" in paths["/expenses/export/pdf"]["get"]["responses"]["200"]["content"]


def test_list_endpoint_documents_the_filters(generated_schema):
    parameters = {p["name"] for p in generated_schema["paths"]["/expenses"]["get"]["parameters"]}
    assert {"from_date", "to_date", "period", "category", "page", "limit"} <= parameters


class TestDocsEndpoints:
    def test_schema_endpoint_is_public_and_valid_yaml(self, client):
        response = client.get("/api/schema")
        assert response.status_code == 200
        assert yaml.safe_load(response.content)["info"]["title"] == "Expense Tracker API"

    def test_swagger_ui_and_redoc_load(self, client):
        for url in ("/api/docs", "/api/redoc"):
            response = client.get(url)
            assert response.status_code == 200
            assert b"/api/schema" in response.content
