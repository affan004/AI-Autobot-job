import os

import pytest
from playwright.sync_api import sync_playwright

from job_portals.greenhouse.job_page_playwright import GreenhouseJobPagePlaywright
from job_portals.lever.job_page_playwright import LeverJobPagePlaywright
from job_portals.workday.job_page_playwright import WorkdayJobPagePlaywright


RUN_LIVE_SMOKE = os.getenv("RUN_LIVE_SMOKE", "").lower() == "true"


@pytest.mark.integration
def test_live_portal_smoke_navigation_and_extraction():
    if not RUN_LIVE_SMOKE:
        pytest.skip("Set RUN_LIVE_SMOKE=true to run live ATS smoke checks.")

    urls = [
        ("lever", "https://jobs.lever.co/plaid/f783a8c4-8ae2-4646-b4f3-a194940ff3b2"),
        (
            "greenhouse",
            "https://job-boards.greenhouse.io/bluestaqaus/jobs/4110854009",
        ),
        (
            "workday",
            "https://lindenwood.wd1.myworkdayjobs.com/CareerOpportunities/job/St-Charles-Campus/Assistant-Coach--Women-s-Volleyball_R0015607",
        ),
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        handlers = {
            "lever": LeverJobPagePlaywright(page),
            "greenhouse": GreenhouseJobPagePlaywright(page),
            "workday": WorkdayJobPagePlaywright(page),
        }

        for kind, url in urls:
            page.goto(url, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_timeout(6000)

            handler = handlers[kind]
            description = handler.get_job_description(None)
            location = handler.get_location()
            categories = handler.get_job_categories()

            assert len(description or "") > 100
            assert isinstance(location, str)
            assert isinstance(categories, dict)

            if kind == "lever":
                apply = page.locator("a.postings-btn.template-btn-submit").first
            elif kind == "greenhouse":
                apply = page.locator("button:has-text('Apply')").first
            else:
                apply = page.locator("a:has-text('Apply')").first

            assert apply.count() > 0
            assert apply.is_visible()

        browser.close()

