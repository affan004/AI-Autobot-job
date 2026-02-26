from typing import List, Optional
from urllib.parse import urlparse
from constants import COMPANY
from job import Job, JobState
from job_portals.base_job_portal import BaseJobsPage
from logger import logger
import stringcase
from  services.web_search_engine import SearchQueryBuilder, SearchResult, SearchTimeRange, WebSearchEngine, WebSearchEngineFactory


class SearchLeverJobs(BaseJobsPage):
    """
    Searches for job postings on Lever-hosted pages by querying a web
    search engine (e.g., Google, Bing, Brave) using advanced site-based
    queries. Collects relevant links and converts them into Job objects.
    """

    def __init__(self, driver, work_preferences):
        """
        :param driver: A webdriver instance (if needed for further scraping).
        :param work_preferences: A dictionary containing filters such as
                                 remote/hybrid/onsite, experience levels,
                                 job type, etc.
        """
        super().__init__(driver, work_preferences)
        self.search_engine = WebSearchEngineFactory.get_search_engine() 
        self.search_offset = 0
        self.search_limit = self.search_engine.DEFAULT_SEARCH_LIMIT 
        self.jobs = []
        self.current_query = None
        self.is_playwright = all(
            hasattr(driver, attr) for attr in ("goto", "locator", "wait_for_load_state")
        )
        self.source_sites = (
            [
                "jobs.lever.co",
                "boards.greenhouse.io",
                "myworkdayjobs.com",
                "workdayjobs.com",
            ]
            if self.is_playwright
            else ["jobs.lever.co"]
        )

     
    def next_job_page(self, position: str, location: str, page_number: int) -> None:
        """
        Moves to the next 'page' of search results by using offset-based pagination.
        
        :param position: The role or title to search for (e.g., "Software Engineer").
        :param location: The location to search in (e.g., "Germany").
        :param page_number: The page number being requested.
        """
        
        # Update pagination offset
        self.search_offset = page_number * self.search_limit

        # Build a unified query using SearchQueryBuilder
        query_builder = SearchQueryBuilder.create()
        
        # Add position and location to keywords.
        # We source from ATS pages directly to avoid high-friction aggregators.
        query_builder.add_source_sites(self.source_sites)
        query_builder.add_to_keywords(
            "(inurl:/apply OR inurl:/jobs OR inurl:/job OR inurl:/en-US/ OR inurl:/Recruiting/)"
        )
        query_builder.add_to_keywords(position)
        query_builder.add_to_keywords(["visa sponsorship", "work authorization"])
        query_builder.set_geolocation(location)

        # Apply blacklists (location, company, title)
        if 'location_blacklist' in self.work_preferences:
            query_builder.add_to_blacklist(self.work_preferences['location_blacklist'])
        
        if 'company_blacklist' in self.work_preferences:
            query_builder.add_to_blacklist(self.work_preferences['company_blacklist'])
        
        if 'title_blacklist' in self.work_preferences:
            query_builder.add_to_blacklist(self.work_preferences['title_blacklist'])

        # Add date range filters
        if 'date' in self.work_preferences:
            if self.work_preferences['date'].get('24_hours', False):
                query_builder.set_date_range(SearchTimeRange.LAST_24_HOURS)
            elif self.work_preferences['date'].get('week', False):
                query_builder.set_date_range(SearchTimeRange.LAST_WEEK)
            elif self.work_preferences['date'].get('month', False):
                query_builder.set_date_range(SearchTimeRange.LAST_MONTH)

        # Add job types and experience levels as whitelists
        if 'job_types' in self.work_preferences:
            job_types = [key for key, enabled in self.work_preferences['job_types'].items() if enabled]
            query_builder.add_to_whitelist(job_types)

        if 'experience_level' in self.work_preferences:
            experience_levels = [key for key, enabled in self.work_preferences['experience_level'].items() if enabled]
            query_builder.add_to_whitelist(experience_levels)

        # whitelist as per work_preferences is not same as whitelist in search engine, workpreferences whitelist forces all words to be present in search result
        if 'keywords_whitelist' in self.work_preferences and self.work_preferences['keywords_whitelist']:
            query_builder.add_to_keywords(self.work_preferences['keywords_whitelist'])
        
        # Translate the unified query into a search-engine-specific query
        final_query, params = query_builder.build_query_for_engine(self.search_engine)
        
        # Store the final query for logging/debugging purposes
        self.current_query = final_query
        
        logger.info(f"Querying '{self.current_query}' with offset={self.search_offset}, limit={self.search_limit}, and params={params}")

        # Execute the search request using the chosen engine
        response = self.search_engine.search(
            query=final_query,
            params=params,
            offset=self.search_offset,
            limit=self.search_limit
        )

        logger.info(f"Found {len(response.results)} results for query '{self.current_query}'")

        # Store the results
        self.jobs = response.results


    def job_tile_to_job(self, job_tile: SearchResult) -> Job:
        """
        Converts a single search result (title, link, snippet) to a Job object.
        The snippet can be used to detect partial location or keywords.
        
        :param job_tile: A SearchResult object with (title, link, snippet).
        :return: A fully populated Job object.
        """
        raw_link = job_tile.link.strip()
        lowered = raw_link.lower()

        portal = "Lever"
        if "greenhouse.io" in lowered:
            portal = "Greenhouse"
        elif "myworkdayjobs.com" in lowered or "workdayjobs.com" in lowered:
            portal = "Workday"

        cleaned_link = raw_link
        if portal == "Lever" and lowered.endswith("/apply"):
            cleaned_link = raw_link[:-6]

        job_id = ""
        company = ""
        try:
            parsed = urlparse(cleaned_link)
            path_parts = [part for part in parsed.path.split("/") if part]

            if portal == "Greenhouse":
                # Typical format: /<company>/jobs/<job-id>
                if path_parts:
                    company = path_parts[0]
                if "jobs" in path_parts:
                    jobs_index = path_parts.index("jobs")
                    if jobs_index + 1 < len(path_parts):
                        job_id = path_parts[jobs_index + 1]
                if not job_id and path_parts:
                    job_id = path_parts[-1]
            elif portal == "Workday":
                host_parts = [part for part in (parsed.hostname or "").split(".") if part]
                if host_parts:
                    # Typical host shape: <company>.wdX.myworkdayjobs.com
                    company = host_parts[0]

                if "job" in path_parts:
                    job_index = path_parts.index("job")
                    if job_index + 1 < len(path_parts):
                        # Workday often puts a location segment after /job/, with id at tail.
                        job_id = path_parts[-1]
                elif path_parts:
                    job_id = path_parts[-1]
            else:
                if path_parts:
                    job_id = path_parts[-1]
                if len(path_parts) >= 2:
                    company = path_parts[-2]

            logger.debug(
                f"Extracted portal={portal}, job ID={job_id} and company={company}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to extract job ID and company from link: {cleaned_link}, error: {e}"
            )

        # Create and populate Job object
        job = Job(
            portal=portal,
            id=job_id,
            title=job_tile.title,
            company=company,
            link=cleaned_link,
            job_state=JobState.APPLY.value,
        )

        logger.debug(f"Created Job object: {job}")
        
        return job


    def get_jobs_from_page(self, scroll=False) -> List[SearchResult]:
        """
        Collects jobs from the current set of search results, transforms
        each link into a Job object, and returns the filtered list.
        
        :param scroll: (Not used here) If controlling a browser, you might
                       scroll for dynamic pages.
        :return: A list of Job objects from the current set of results.
        """
        return self.jobs
        

