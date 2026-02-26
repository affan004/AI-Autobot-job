from job_portals.lever.multi_ats_playwright import (
    MultiAtsApplicationPagePlaywright,
    MultiAtsJobPagePlaywright,
)


class FakeDriver:
    def __init__(self):
        self.url = ""


def test_multi_ats_job_page_routing_by_url():
    driver = FakeDriver()
    router = MultiAtsJobPagePlaywright(driver)

    assert router._page_for_url("https://jobs.lever.co/company/abc/apply") is router.lever_page
    assert router._page_for_url("https://boards.greenhouse.io/company/jobs/123") is router.greenhouse_page
    assert router._page_for_url("https://x.wd1.myworkdayjobs.com/en-US/careers/job/City/Role_123") is router.workday_page


def test_multi_ats_application_page_routing_by_current_url():
    driver = FakeDriver()
    router = MultiAtsApplicationPagePlaywright(driver)

    driver.url = "https://jobs.lever.co/company/abc/apply"
    assert router._delegate() is router.lever_page

    driver.url = "https://boards.greenhouse.io/company/jobs/123"
    assert router._delegate() is router.greenhouse_page

    driver.url = "https://x.wd1.myworkdayjobs.com/en-US/careers/job/City/Role_123"
    assert router._delegate() is router.workday_page

