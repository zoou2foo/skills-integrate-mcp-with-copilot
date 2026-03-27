"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

from storage import (
    ActivityFullError,
    ActivityNotFoundError,
    ActivityRepository,
    AlreadySignedUpError,
    NotSignedUpError,
)

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

repository = ActivityRepository(
    db_path=current_dir / "data" / "school.db",
    seed_file_path=current_dir / "data" / "seed_activities.json",
)


@app.on_event("startup")
def startup() -> None:
    repository.initialize_database()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return repository.list_activities()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    try:
        repository.signup(activity_name=activity_name, email=email)
    except ActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Activity not found") from exc
    except AlreadySignedUpError as exc:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up",
        ) from exc
    except ActivityFullError as exc:
        raise HTTPException(
            status_code=400,
            detail="Activity is full",
        ) from exc

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    try:
        repository.unregister(activity_name=activity_name, email=email)
    except ActivityNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Activity not found") from exc
    except NotSignedUpError as exc:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity",
        ) from exc

    return {"message": f"Unregistered {email} from {activity_name}"}
