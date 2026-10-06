"""Domain tools for the UAE Labour Law pack. Deterministic, unit-tested, and cited.

The LLM decides WHEN to call a tool and EXPLAINS the result; the code does the maths.
"""

DAYS_PER_MONTH = 30  # Assumption: daily basic wage = monthly basic / 30 (common practice)
FIRST_TIER_YEARS = 5
FIRST_TIER_DAYS = 21
SECOND_TIER_DAYS = 30
CAP_MONTHS = 24      # total capped at two years' wage

LEGAL_BASIS = (
    "Federal Decree-Law 33/2021, Article 51 (PDF page 19): 21 days' basic wage per year for the "
    "first 5 years, 30 days per additional year, fractions pro rata, unpaid absence excluded, "
    "total capped at two years' wage; minimum one year of continuous service."
)


def calculate_gratuity(basic_monthly_wage: float, years_of_service: float, unpaid_absence_days: int = 0) -> dict:
    if basic_monthly_wage <= 0 or years_of_service < 0 or unpaid_absence_days < 0:
        return {"error": "basic_monthly_wage must be > 0; years_of_service and unpaid_absence_days must be >= 0"}

    effective_years = max(0.0, years_of_service - unpaid_absence_days / 365)
    daily = basic_monthly_wage / DAYS_PER_MONTH
    assumptions = [
        "Full-time private-sector worker",
        "Daily wage = monthly BASIC wage / 30 (allowances excluded)",
        "Does not include deductions the employer may lawfully make (Article 51)",
        "General information, not legal advice; confirm with MOHRE",
    ]

    if effective_years < 1:
        return {
            "eligible": False, "amount_aed": 0.0,
            "reason": "Less than one year of continuous service (after excluding unpaid absence).",
            "effective_years": round(effective_years, 3),
            "legal_basis": LEGAL_BASIS, "assumptions": assumptions,
        }

    first_years = min(effective_years, FIRST_TIER_YEARS)
    extra_years = max(0.0, effective_years - FIRST_TIER_YEARS)
    first_amount = first_years * FIRST_TIER_DAYS * daily
    extra_amount = extra_years * SECOND_TIER_DAYS * daily
    uncapped = first_amount + extra_amount
    cap = basic_monthly_wage * CAP_MONTHS
    amount = min(uncapped, cap)

    return {
        "eligible": True,
        "amount_aed": round(amount, 2),
        "breakdown": {
            "effective_years": round(effective_years, 3),
            "daily_basic_wage": round(daily, 2),
            "first_5_years": f"{first_years:g} yrs x 21 days x {daily:.2f} = {first_amount:,.2f}",
            "after_5_years": f"{extra_years:g} yrs x 30 days x {daily:.2f} = {extra_amount:,.2f}",
            "cap_aed": round(cap, 2),
            "cap_applied": uncapped > cap,
        },
        "legal_basis": LEGAL_BASIS,
        "assumptions": assumptions,
    }


GRATUITY_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_gratuity",
        "description": (
            "Calculate UAE end-of-service gratuity (end of service benefits) for a full-time "
            "private-sector worker. Use whenever the user wants an amount. Ask for the BASIC "
            "monthly wage and years of service if missing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "basic_monthly_wage": {"type": "number", "description": "Monthly BASIC wage in AED, excluding allowances"},
                "years_of_service": {"type": "number", "description": "Total continuous years of service; decimals allowed, e.g. 6.5"},
                "unpaid_absence_days": {"type": "integer", "description": "Days of unpaid absence to exclude; 0 if unknown"},
            },
            "required": ["basic_monthly_wage", "years_of_service"],
        },
    },
}

TOOLS = {"calculate_gratuity": (GRATUITY_TOOL, calculate_gratuity)}
