import asyncio
import random
import re
from datetime import datetime
from typing import Optional, Dict, Any

from loguru import logger
from playwright.async_api import async_playwright, Page, BrowserContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from core.config import settings
from database.models import Car


class AutoRiaScraper:
    """Main Scraper Service for AutoRia.

    Responsible for collecting car data from AutoRia listings and persisting
    it to a PostgreSQL database. Implements concurrency control via semaphores,
    browser context management, and robust error handling.

    Attributes:
        db (AsyncSession): The SQLAlchemy async session for database operations.
        context (Optional[BrowserContext]): The Playwright browser context.
        semaphore (asyncio.Semaphore): Concurrency limiter for scraping tasks.
    """
    def __init__(self, db: AsyncSession, semaphore_limit: int = 3):
            """Initializes the scraper with a database session and concurrency controls.

            Args:
                db (AsyncSession): An active asynchronous SQLAlchemy session.
                semaphore_limit (int, optional): The maximum number of concurrent
                    scraping tasks (browser tabs) allowed. Defaults to 3.
            """
            self.db = db
            self.context: Optional[BrowserContext] = None
            self.semaphore = asyncio.Semaphore(semaphore_limit)

    async def run(self):
        """Executes the main scraping workflow.

        Launches the Playwright browser, sets up the context with a realistic
        User-Agent, and initiates the catalog crawling process. Handles the
        browser lifecycle (launching and closing) and logs critical stages.
        """
        logger.info(f"🚀 Starting scraper from URL: {settings.START_URL}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            self.context = await browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )

            page = await self.context.new_page()

            try:
                await self._get_cars_urls(page)
            except Exception as e:
                logger.error(f"Critical scraper error: {e}")
            finally:
                await browser.close()
                logger.info("Scraper finished execution.")

    async def _get_cars_urls(self, page: Page) -> list[str]:
        """Iterates through all pagination pages to collect car links.

        Navigates through the catalog starting from the configured start URL.
        On each page, it extracts car links and spawns asynchronous tasks to
        scrape details for each car, respecting the semaphore limits.

        Args:
            page (Page): The Playwright page object used for navigation.

        Returns:
            list[str]: A list of collected car URLs (used internally).
        """
        current_url = settings.START_URL

        while True:
            logger.info(f"Processing catalog page: {current_url}")
            try:
                await page.goto(current_url, timeout=60000)
                await page.wait_for_selector(".ticket-item", state="attached")
            except Exception as e:
                logger.error(f"Failed to load catalog: {e}")
                break

            links_locators = await page.locator("a.m-link-ticket").all()
            car_links = [await link.get_attribute("href") for link in links_locators]

            logger.info(f"Found {len(car_links)} cars on the current page.")

            # Async processing of car links
            tasks = [self._safe_get_car_data(link) for link in car_links]
            await asyncio.gather(*tasks)

            # Sync processing of car links
            # for link in car_links:
            #     await self._get_car_data(link)
            #     asyncio.sleep(random.uniform(5, 15))

            next_page_btn = page.locator("a.page-link.js-next")

            if await next_page_btn.is_visible():
                current_url = await next_page_btn.get_attribute("href")
                logger.info("Navigating to the next page...")
            else:
                logger.info("Reached the last page.")
                break

    async def _safe_get_car_data(self, link: str):
        """Wrapper to scrape car data respecting the concurrency semaphore.

        Ensures that the number of concurrent browser tabs/contexts does not
        exceed the limit defined in `self.semaphore`.

        Args:
            link (str): The URL of the specific car listing to scrape.
        """
        async with self.semaphore:
            await self._get_car_data(link)

    async def _get_car_data(self, link: str):
        """Visits a single car page, scrapes data, and saves it to the DB.

        Opens a new page context, extracts fields (title, price, odometer, etc.),
        handles the phone number popup, and saves the data to the database using
        an upsert operation.

        Args:
            link (str): The URL of the car listing.
        """

        await asyncio.sleep(random.uniform(3, 7))

        page = await self.context.new_page()
        try:
            logger.debug(f"🔍 Scraping car: {link}")
            await page.goto(link, timeout=45000)

            auto_id = await page.locator("#advertStatisticID .titleS").text_content()

            if not auto_id:
                match = re.search(r"_(\d+)\.html", link)
                if match:
                    auto_id = match.group(1)

            if not auto_id:
                logger.warning(f"WARNING: Could not determine auto_id for {link}. Skipping.")
                return

            title = await page.locator("#basicInfoTitle").first.text_content()

            price_text = await page.locator("#basicInfoPrice .titleL").text_content()
            price_usd = self._clean_price(price_text)

            odometer_text = await page.locator(
                "#basicInfoTableMainInfo0 span"
            ).first.text_content()
            odometer = self._clean_odometer(odometer_text)

            username = await page.locator(
                "#sellerInfoUserName .titleM"
            ).first.text_content()
            username = username.strip() if username else "Unknown"

            vin_locator = page.locator("#badgesVin span.badge")
            car_vin = (
                await vin_locator.text_content()
                if await vin_locator.is_visible()
                else None
            )

            plate_locator = page.locator("div.car-number span.common-text").first
            car_number = (
                await plate_locator.text_content()
                if await plate_locator.is_visible()
                else None
            )

            image_url = await page.locator(
                "div.carousel__viewport img"
            ).first.get_attribute("src")
            
            photo_count_text = await page.locator(
                '#photoSlider .carousel__liveregion[aria-live="polite"]'
            ).text_content()
            images_count = self._clean_photo_count(photo_count_text)

            phone_number = await self._fetch_phone_number(page)

            car_data = {
                "url": link,
                "title": title.strip(),
                "price_usd": price_usd,
                "odometer": odometer,
                "username": username,
                "phone_number": phone_number,
                "image_url": image_url,
                "images_count": images_count,
                "car_number": car_number.strip() if car_number else None,
                "car_vin": car_vin.strip() if car_vin else None,
                "datetime_found": datetime.now(),
            }

            await self._save_to_db(car_data)
            logger.debug(f"Scraped data: {car_data}")

        except Exception as e:
            logger.error(f"Error processing {link}: {e}")
        finally:
            await page.close()

    async def _fetch_phone_number(self, page: Page) -> Optional[int]:
        """Attempts to retrieve the hidden phone number from the listing.

        Simulates a click on the 'Show Phone' button and waits for the popup
        to appear. Parses the resulting text to extract the number.

        Args:
            page (Page): The current page object for the specific car listing.

        Returns:
            Optional[int]: The cleaned phone number as an integer, or None if extraction fails.
        """
        show_phone_button = page.locator(
            "#sellerInfo div.button-main button[data-action='showBottomPopUp']"
        )

        logger.debug("Attempting to click 'Show Phone' button")
        try:
            await show_phone_button.click(timeout=10000)
        except Exception as e:
            logger.warning(f"Could not click 'Show Phone' button: {e}")
            return None

        popup_locator = page.locator(
            "#autoPhonePopUpResponse div.button-main span.common-text"
        ).first

        await popup_locator.wait_for(state="visible", timeout=10000)

        phone_text = await popup_locator.text_content()
        phone_number = self._clean_phone(phone_text)

        return phone_number

    async def _save_to_db(self, data: Dict[str, Any]):
        """Persists scraped car data to the database using an UPSERT operation.

        Uses PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE` syntax to ensure
        records are updated if they already exist (based on the unique URL),
        or inserted if they are new.

        Args:
            data (Dict[str, Any]): A dictionary containing the car attributes.
        """
        stmt = pg_insert(Car).values(**data)

        do_update_stmt = stmt.on_conflict_do_update(index_elements=["url"], set_=data)

        await self.db.execute(do_update_stmt)
        await self.db.commit()
        logger.info(f"Saved/Updated car: {data['title']}")

    @staticmethod
    def _clean_price(text: Optional[str]) -> Optional[int]:
        """Parses the price string into an integer.

        Args:
            text (Optional[str]): The raw price string (e.g., '15 500 $').

        Returns:
            Optional[int]: The price as an integer (e.g., 15500), or None if parsing fails.
        """
        if not text:
            return None
        clean = re.sub(r"\D", "", text)
        return int(clean) if clean else None

    @staticmethod
    def _clean_odometer(text: Optional[str]) -> Optional[int]:
        """Parses the odometer string, handling 'thousand' multipliers.

        Args:
            text (Optional[str]): The raw odometer string (e.g., '95 тис. км').

        Returns:
            Optional[int]: The distance in kilometers (e.g., 95000), or None if parsing fails.
        """
        if not text:
            return None
        text = text.lower()
        numbers = re.sub(r"\D", "", text)
        if not numbers:
            return None

        val = int(numbers)
        if "тис" in text:
            val *= 1000
        return val

    @staticmethod
    def _clean_photo_count(text: Optional[str]) -> Optional[int]:
        """Extracts the total number of photos from the gallery text.

        Args:
            text (Optional[str]): The gallery text (e.g., 'Photo 1 of 19').

        Returns:
            Optional[int]: The total count of photos (e.g., 19), or None if extraction fails.
        """
        if not text:
            return None

        match = re.search(r"(\d+)$", text)

        if match:
            photos_count_str = match.group(1)
            try:
                return int(photos_count_str)
            except ValueError:
                return None

        return None

    @staticmethod
    def _clean_phone(text: str) -> Optional[int]:
        """Normalizes phone number strings to a standard integer format.

        Removes non-digit characters and adds the country code (380) if missing.

        Args:
            text (str): The raw phone string (e.g., '(063) 213 44 11').

        Returns:
            Optional[int]: The normalized phone number (e.g., 380632134411), or None.
        """
        if not text:
            return None
        clean = re.sub(r"\D", "", text)
        if not clean:
            return None

        if len(clean) == 10:
            clean = "38" + clean
        elif len(clean) == 9:
            clean = "380" + clean

        return int(clean)
