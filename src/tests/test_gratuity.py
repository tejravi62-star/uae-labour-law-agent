import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "packs" / "uae-labour-law"))
from tools import calculate_gratuity  # noqa: E402


def test_under_one_year_not_eligible():
    r = calculate_gratuity(10000, 0.9)
    assert r["eligible"] is False and r["amount_aed"] == 0


def test_exactly_five_years():
    # 5 x 21 x (9000/30=300) = 31,500
    assert calculate_gratuity(9000, 5)["amount_aed"] == 31500


def test_six_years_two_tiers():
    # 5 x 21 x 400 = 42,000 + 1 x 30 x 400 = 12,000 -> 54,000
    assert calculate_gratuity(12000, 6)["amount_aed"] == 54000


def test_fraction_pro_rata():
    # 2.5 x 21 x 300 = 15,750
    assert calculate_gratuity(9000, 2.5)["amount_aed"] == 15750


def test_unpaid_absence_reduces_service():
    # 6 years minus 365 unpaid days = 5 effective years -> 5 x 21 x 400 = 42,000
    assert calculate_gratuity(12000, 6, 365)["amount_aed"] == 42000


def test_cap_two_years_wage():
    r = calculate_gratuity(10000, 30)
    assert r["amount_aed"] == 240000 and r["breakdown"]["cap_applied"] is True


def test_invalid_input():
    assert "error" in calculate_gratuity(-1, 5)


def test_result_is_cited():
    r = calculate_gratuity(12000, 6)
    assert "Article 51" in r["legal_basis"] and r["assumptions"]
