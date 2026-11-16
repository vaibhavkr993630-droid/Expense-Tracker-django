import csv
import io
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.expenses import exports

pytestmark = pytest.mark.django_db


def read_csv(response):
    """Parse a streaming CSV response into a list of rows."""
    content = b"".join(response.streaming_content).decode("utf-8")
    return list(csv.reader(io.StringIO(content)))


class TestAuth:
    @pytest.mark.parametrize("url", ["/expenses/export/csv", "/expenses/export/pdf"])
    def test_requires_authentication(self, api_client, url):
        assert api_client.get(url).status_code == 401


class TestCsv:
    def test_headers_and_rows(self, auth_client, user, make_expense):
        old = make_expense(user, amount="10.5", category="Health", description="Vitamins", date="2026-01-01")
        new = make_expense(user, amount="99", category="Groceries", description="", date="2026-03-01")
        response = auth_client.get("/expenses/export/csv")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        today = timezone.localdate()
        assert response["Content-Disposition"] == f'attachment; filename="expenses_{today:%Y%m%d}.csv"'
        assert read_csv(response) == [
            ["ID", "Date", "Category", "Amount", "Description"],
            [str(new.id), "2026-03-01", "Groceries", "99.00", ""],  # newest first
            [str(old.id), "2026-01-01", "Health", "10.50", "Vitamins"],
        ]

    def test_empty_export_still_has_the_header(self, auth_client):
        assert read_csv(auth_client.get("/expenses/export/csv")) == [
            ["ID", "Date", "Category", "Amount", "Description"]
        ]

    def test_only_own_expenses(self, auth_client, user, other_user, make_expense):
        mine = make_expense(user)
        make_expense(other_user, description="secret")
        rows = read_csv(auth_client.get("/expenses/export/csv"))
        assert [row[0] for row in rows[1:]] == [str(mine.id)]

    def test_uses_the_same_filters_as_the_list(self, auth_client, user, make_expense):
        today = timezone.localdate()
        recent = make_expense(user, date=today - timedelta(days=2), category="Health")
        make_expense(user, date=today - timedelta(days=100), category="Health")
        make_expense(user, date=today - timedelta(days=1), category="Leisure")
        ids = lambda query: [r[0] for r in read_csv(auth_client.get(f"/expenses/export/csv?{query}"))[1:]]  # noqa: E731
        assert ids("period=week&category=Health") == [str(recent.id)]
        assert len(ids("period=week")) == 2
        assert len(ids("from_date=2000-01-01")) == 3

    def test_special_characters_are_escaped_correctly(self, auth_client, user, make_expense):
        make_expense(user, description='Lunch, "big" one\nsecond line')
        rows = read_csv(auth_client.get("/expenses/export/csv"))
        assert rows[1][4] == 'Lunch, "big" one\nsecond line'

    @pytest.mark.parametrize("payload", ['=HYPERLINK("http://evil")', "+1+1", "-2+3", "@SUM(A1)"])
    def test_formula_injection_is_defused(self, auth_client, user, make_expense, payload):
        make_expense(user, description=payload)
        assert read_csv(auth_client.get("/expenses/export/csv"))[1][4] == "'" + payload

    def test_non_ascii_text_is_kept(self, auth_client, user, make_expense):
        make_expense(user, description="₹500 café 你好")
        assert read_csv(auth_client.get("/expenses/export/csv"))[1][4] == "₹500 café 你好"

    def test_is_streamed_and_query_count_is_constant(
        self, auth_client, user, make_expense, django_assert_num_queries
    ):
        for _ in range(30):
            make_expense(user)
        response = auth_client.get("/expenses/export/csv")
        assert response.streaming  # sent while being generated, not built in memory first
        with django_assert_num_queries(1):  # one SELECT for all rows
            b"".join(response.streaming_content)

    @pytest.mark.parametrize(
        "query", ["from_date=2026-05-02&to_date=2026-05-01", "period=decade", "from_date=yesterday"]
    )
    def test_invalid_filters_are_400(self, auth_client, query):
        response = auth_client.get(f"/expenses/export/csv?{query}")
        assert response.status_code == 400
        assert isinstance(response.json()["detail"], str)

    def test_export_route_is_not_treated_as_an_expense_id(self, auth_client):
        assert auth_client.get("/expenses/export/csv").status_code == 200


class TestPdf:
    def test_returns_a_pdf_attachment(self, auth_client, user, make_expense):
        make_expense(user, amount="12.50", description="Milk")
        response = auth_client.get("/expenses/export/pdf")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/pdf"
        assert response["Content-Disposition"].startswith('attachment; filename="expenses_')
        assert response["Content-Disposition"].endswith('.pdf"')
        assert response.content.startswith(b"%PDF")

    def test_empty_export_is_still_a_valid_pdf(self, auth_client):
        assert auth_client.get("/expenses/export/pdf").content.startswith(b"%PDF")

    def test_non_latin_text_does_not_crash(self, auth_client, user, make_expense):
        make_expense(user, description="₹500 café 你好 😀")
        response = auth_client.get("/expenses/export/pdf")
        assert response.status_code == 200 and response.content.startswith(b"%PDF")

    def test_many_rows_span_several_pages(self, auth_client, user, make_expense):
        for _ in range(120):
            make_expense(user, description="row")
        content = auth_client.get("/expenses/export/pdf").content
        assert content.startswith(b"%PDF") and len(content) > 5000

    def test_receives_only_own_filtered_rows_and_the_real_period(
        self, auth_client, user, other_user, make_expense
    ):
        mine = make_expense(user, date=timezone.localdate())
        make_expense(user, date=timezone.localdate() - timedelta(days=200))
        make_expense(other_user, date=timezone.localdate())
        with patch("apps.expenses.views.exports.build_expenses_pdf", return_value=b"%PDF-fake") as build:
            auth_client.get("/expenses/export/pdf?period=week")
        expenses, username, from_date, to_date = build.call_args.args[:4]
        assert expenses == [mine] and username == "alice"
        assert to_date == timezone.localdate() and from_date == to_date - timedelta(days=7)

    def test_too_many_rows_is_refused_with_a_hint(self, auth_client, user, make_expense):
        for _ in range(4):
            make_expense(user)
        with patch.object(exports, "PDF_MAX_ROWS", 3):
            response = auth_client.get("/expenses/export/pdf")
        assert response.status_code == 400
        assert "Too many expenses for a PDF" in response.json()["detail"]

    @pytest.mark.parametrize("query", ["from_date=2026-05-02&to_date=2026-05-01", "period=decade"])
    def test_invalid_filters_are_400(self, auth_client, query):
        assert auth_client.get(f"/expenses/export/pdf?{query}").status_code == 400


class TestExportThrottle:
    def test_exports_are_rate_limited(self, auth_client):
        statuses = [auth_client.get("/expenses/export/csv").status_code for _ in range(31)]
        assert statuses[:30] == [200] * 30
        assert statuses[30] == 429


class TestHelpers:
    def test_latin1_replaces_unsupported_characters(self):
        assert exports._latin1("café ₹ 你") == "café ? ?"

    def test_csv_safe_leaves_normal_text_alone(self):
        assert exports._csv_safe("Groceries - milk") == "Groceries - milk"
        assert exports._csv_safe("") == ""
