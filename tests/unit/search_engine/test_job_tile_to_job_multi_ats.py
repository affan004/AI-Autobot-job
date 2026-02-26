from job_portals.lever.jobs_page import SearchLeverJobs
from services.web_search_engine import SearchResult


class DummyDriver:
    def goto(self, *_args, **_kwargs):
        return None

    def locator(self, *_args, **_kwargs):
        return None

    def wait_for_load_state(self, *_args, **_kwargs):
        return None


def test_job_tile_to_job_lever_mapping():
    jobs_page = SearchLeverJobs(DummyDriver(), work_preferences={})
    result = SearchResult(
        title="Software Engineer",
        link="https://jobs.lever.co/jobgether/94ab1e78-ea17-4744-8bc2-59f9f354774c/apply",
        snippet="",
    )

    job = jobs_page.job_tile_to_job(result)
    assert job.portal == "Lever"
    assert job.company == "jobgether"
    assert job.id == "94ab1e78-ea17-4744-8bc2-59f9f354774c"
    assert not job.link.endswith("/apply")


def test_job_tile_to_job_greenhouse_mapping():
    jobs_page = SearchLeverJobs(DummyDriver(), work_preferences={})
    result = SearchResult(
        title="Senior Systems Engineer",
        link="https://job-boards.greenhouse.io/bluestaqaus/jobs/4110854009",
        snippet="",
    )

    job = jobs_page.job_tile_to_job(result)
    assert job.portal == "Greenhouse"
    assert job.company == "bluestaqaus"
    assert job.id == "4110854009"


def test_job_tile_to_job_workday_mapping():
    jobs_page = SearchLeverJobs(DummyDriver(), work_preferences={})
    result = SearchResult(
        title="Assistant Professor",
        link="https://lindenwood.wd1.myworkdayjobs.com/CareerOpportunities/job/St-Charles-Campus/Assistant-Associate-Professor--Mathematics_R0015136",
        snippet="",
    )

    job = jobs_page.job_tile_to_job(result)
    assert job.portal == "Workday"
    assert job.company == "lindenwood"
    assert job.id == "Assistant-Associate-Professor--Mathematics_R0015136"

