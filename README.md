# Formula 1 API Backend

A Django REST Framework backend for a Formula 1 web application. The project provides a structured API for racing data, championship standings, user accounts, favorites, and editorial content that can be consumed by a React frontend.

The backend is organized as a modular Django project with separate apps for racing data, standings, users, shared core utilities, and content management.

## Features

### F1 AI Analyst

Authenticated assistant using pretrained models, Responses API function calling,
read-only ORM tools, and semantic retrieval over published articles. Includes
owned conversations, PostgreSQL/pgvector storage with working SQLite retrieval,
incremental indexing, offline mocked tests, and labeled evaluation cases.
See [AI architecture, setup, API, and evaluation](docs/ai-analyst.md).

### Racing Data

- Seasons, teams, drivers, circuits, and races
- Race calendar support with current season, upcoming race, and latest race endpoints
- Race results with positions, grid positions, laps, fastest laps, points, and race status
- Qualifying results with Q1, Q2, and Q3 timing fields
- Sprint results with sprint positions, grid positions, points, and status
- Search, filtering, ordering, and pagination for list endpoints

### Championship Standings

- Driver championship standings by season
- Constructor championship standings by season
- Standing statistics such as points, wins, podiums, poles, fastest laps, race entries, finishes, DNFs, double podiums, and double points finishes

### Users and Authentication

- Custom UUID-based user model
- JWT authentication with access, refresh, and token verification endpoints
- User registration
- Current authenticated user endpoint
- User profile endpoint with avatar, country, bio, and favorite driver/team names
- Password change and password reset flow
- User dashboard summary

### Favorites

Authenticated users can save and manage:

- Favorite drivers
- Favorite teams
- Favorite races

The API prevents duplicate favorites per user.

### Content and Articles

- Categories and tags
- Article/news publishing system
- Draft, published, and archived article states
- Featured articles
- Article detail by UUID or slug
- Article relationships to races, drivers, and teams
- Automatic slug generation
- View count tracking
- Public users see published content, while staff users can manage broader content states

### API Quality

- OpenAPI schema generation with drf-spectacular
- Swagger UI and ReDoc documentation
- Shared success and error response helpers
- Admin-only write access for public racing, standings, and content resources
- Public read access for public resources
- Centralized pagination, filtering, searching, ordering, and exception handling
- CORS support for React development clients
- Demo data seeding command for local development

## Tech Stack

- Python
- Django
- Django REST Framework
- Simple JWT
- django-filter
- django-cors-headers
- drf-spectacular
- Pillow
- python-decouple
- SQLite for local development

## Project Structure

```txt
.
├── apps/
│   ├── ai/            # LLM tools, article RAG, conversations, and evaluations
│   ├── content/       # Categories, tags, articles, and featured content
│   ├── core/          # Shared responses, permissions, pagination, utilities
│   ├── racing/        # Seasons, teams, drivers, circuits, races, and results
│   ├── standings/     # Driver and constructor standings
│   └── users/         # Custom users, profiles, authentication, favorites
├── config/
│   ├── settings/      # Base, development, and production settings modules
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
├── manage.py
└── README.md
```

## Main API Areas

### Racing

Base path: `/api/racing/`

- `/seasons/`
- `/seasons/current/`
- `/teams/`
- `/drivers/`
- `/circuits/`
- `/races/`
- `/races/upcoming/`
- `/races/latest/`
- `/race-results/`
- `/qualifying-results/`
- `/sprint-results/`

### Standings

Base path: `/api/standings/`

- `/drivers/`
- `/constructors/`

### Users

Base path: `/api/users/`

- `/register/`
- `/token/`
- `/token/refresh/`
- `/token/verify/`
- `/me/`
- `/profile/`
- `/dashboard/`
- `/favorites/drivers/`
- `/favorites/teams/`
- `/favorites/races/`
- `/password/change/`
- `/password/reset/`
- `/password/reset/confirm/`

### Content

Base path: `/api/content/`

- `/categories/`
- `/tags/`
- `/articles/`
- `/articles/featured/`
- `/articles/<uuid>/`
- `/articles/slug/<slug>/`

## API Documentation

When the development server is running, interactive API documentation is available at:

```txt
/api/docs/    # Swagger UI
/api/redoc/   # ReDoc
/api/schema/  # OpenAPI schema
```

## API Request Screenshots

The screenshots below show example API requests tested with Postman.

### Get Drivers

![Get drivers request](docs/screenshots/get_drivers.png)

### Create Circuit

![Post circuit request](docs/screenshots/post_circuit.png)

### Update Race Result

![Patch driver request](docs/screenshots/patch_raceresult.png)

### Delete Race Result

![Delete race result request](docs/screenshots/delete_raceresult.png)


## Local Development

Install dependencies:

```bash
pip install -r requirements/development.txt
```

Create an environment file from the example:

```bash
cp .env.example .env
```

Run migrations:

```bash
python manage.py migrate
```

Optionally seed demo data:

```bash
python manage.py seed_demo_data
```

Start the development server:

```bash
python manage.py runserver
```

## Notes

This repository contains the backend API for the Formula 1 web application. It is designed to pair with a React frontend and focuses on providing clean, structured data for race information, standings, personalized user features, and F1-related editorial content.
