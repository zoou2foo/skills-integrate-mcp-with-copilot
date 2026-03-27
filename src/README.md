# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities
- Unregister students from activities
- Persistent SQLite storage for activities, participants, and enrollments

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Run the application:

   ```
   python app.py
   ```

   On first run, the app automatically creates `src/data/school.db` and seeds it from `src/data/seed_activities.json`.

3. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |

## Data Model

The application uses a SQLite-backed data model with explicit entities:

1. **Activities**

   - Description
   - Schedule
   - Maximum number of participants allowed
2. **Participants**

   - Student email

3. **Enrollments**

   - Many-to-many relation between activities and participants
   - Enrollment timestamp

The `/activities` API shape remains unchanged and still returns a dictionary keyed by activity name, including each activity's participant email list.

Data persists between restarts in `src/data/school.db`.
