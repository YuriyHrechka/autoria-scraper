# AutoRia Scraper

An asynchronous web scraper designed to collect data on **used cars** from the AutoRia platform. The application is fully containerized with Docker and includes a built-in scheduling system for daily scraping and automated database backups.

## Features

* **Asynchronous Scraping** – Built with **Playwright (async)** and **asyncio** for efficient data collection.
* **Dynamic Content Handling** – Correctly waits for page loads, hidden elements, and delayed content.
* **Smart Filtering** – Excludes dealership and "new car" listings, collecting only used cars.
* **Data Persistence** – Uses **PostgreSQL** with an **Upsert strategy** to prevent duplicates.
* **Automated Scheduling** – Tasks are executed daily using **APScheduler** (default: 12:00 Kyiv time).
* **Database Backups** – Daily automated PostgreSQL dumps via `pg_dump`.
* **Containerized Environment** – Fully managed with **Docker** and **Docker Compose**.

## Tech Stack

* **Python 3.11** (Slim image)
* **Playwright (Async)** – Browser automation
* **SQLAlchemy (Async)** – ORM and database interaction
* **PostgreSQL 15 (Alpine)** – Relational database
* **APScheduler** – Task scheduling
* **Docker & Docker Compose** – Deployment and isolation

## Project Structure

The project follows a modular and scalable architecture:

```text
autoria-scraper/
├── app/
│   ├── core/
│   │   └── config.py        # Application configuration (Pydantic)
│   ├── database/
│   │   ├── models.py        # SQLAlchemy models
│   │   └── session.py       # Async database session management
│   ├── services/
│   │   ├── backup.py        # PostgreSQL backup service (pg_dump)
│   │   └── scraper.py       # Main scraping logic (Playwright)
│   └── main.py              # Application entry point and scheduler setup
├── dumps/                   # Mounted volume for database backups
├── .env                     # Environment variables (git-ignored)
├── .env.example             # Example environment configuration
├── docker-compose.yml       # Docker services configuration
├── Dockerfile               # Python image configuration
└── requirements.txt         # Project dependencies
```

## Collected Data

The application stores the following fields for each car listing in the `cars` table:

* `id` – Primary key
* `url` – Listing URL (unique)
* `title` – Car title
* `price_usd` – Price in USD
* `odometer` – Mileage (converted from thousands of km to a raw number)
* `username` – Seller username
* `phone_number` – Seller phone number (`380...` format)
* `image_url` – Main image URL
* `images_count` – Number of listing images
* `car_number` – License plate number
* `car_vin` – VIN code
* `datetime_found` – Timestamp with timezone

## Installation & Setup

### Steps to Run

1. **Clone the repository:**

```bash
git clone https://github.com/YuriyHrechka/autoria-scraper.git
cd autoria-scraper
```

2. **Configure environment variables:**

Create a `.env` file in the project root (you can copy the example file):

```bash
cp .env.example .env
```

Default `.env` configuration:

```ini
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password_here
POSTGRES_DB=autoria_db
POSTGRES_HOST=db
POSTGRES_PORT=5432

START_URL=https://auto.ria.com/uk/car/used/
RUN_TIME_HOUR=12
RUN_TIME_MINUTE=00
```

3. **Build and run the application:**

```bash
docker-compose up -d --build
```

4. **Verify execution:**

Follow scraper logs to ensure everything is running correctly:

```bash
docker-compose logs -f scraper
```

## License

This project is provided as-is for educational and demonstration purposes.
